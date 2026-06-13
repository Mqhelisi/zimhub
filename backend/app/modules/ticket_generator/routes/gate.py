"""/api/gate/* — standalone gate app endpoints.

PER STAGE_3_SPEC.md §5.5: this is the ONE non-cookie auth surface in ZimHub.
Gatemen log in with phone + PIN + event_id, receive a JWT in the response body,
and clients store it in localStorage. All other auth in the app stays in cookies.

We use the same jwt extension to mint tokens but with a custom additional_claim
('gate_session': True, 'gateman_id', 'event_id') and a separate decorator that
reads the bearer header.
"""
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import (
    create_access_token, decode_token,
)
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.utils.errors import (
    error_response, validation_failed, not_found, unauthenticated,
)
from app.utils.passwords import verify_password
from app.services import host

from ..models import Event, Gateman, Ticket, TicketType
from ..services.scan import scan_ticket


log = logging.getLogger('zimhub.ticket_generator.gate')

gate_bp = Blueprint('tg_gate', __name__, url_prefix='/api/gate')


# ---------------------------------------------------------------------------
# Gateman bearer auth decorator
# ---------------------------------------------------------------------------
def gateman_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Bearer token from Authorization header.
        auth = request.headers.get('Authorization', '')
        if not auth.lower().startswith('bearer '):
            return unauthenticated('Bearer token required.')
        token = auth[7:].strip()
        try:
            payload = decode_token(token)
        except Exception:
            return unauthenticated('Invalid or expired gate token.')
        if not payload.get('gate_session'):
            return unauthenticated('Wrong token kind for the gate.')
        gid = payload.get('gateman_id')
        if not gid:
            return unauthenticated('Token missing gateman_id.')
        gateman = db.session.get(Gateman, gid)
        if not gateman:
            return unauthenticated('Gateman no longer exists.')
        # Auto-lock check.
        now = datetime.now(timezone.utc)
        if gateman.revoked_at is not None:
            return unauthenticated('Gateman access revoked.')
        if gateman.locked_until is not None and gateman.locked_until < now:
            return unauthenticated('Gateman session has expired (event ended).')
        g.gateman = gateman
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@gate_bp.post('/login')
def gate_login():
    """Phone + PIN + event_id → bearer token scoped to that event."""
    data = request.get_json(silent=True) or {}
    phone = (data.get('phone') or '').strip()
    pin = (data.get('pin') or '').strip()
    event_id = (data.get('event_id') or '').strip()

    if not phone or not pin or not event_id:
        return validation_failed('phone, pin and event_id are all required.')

    event = db.session.get(Event, event_id)
    if not event:
        return not_found('Event not found.')

    gateman = (Gateman.query
               .filter(Gateman.event_id == event.id, Gateman.phone == phone)
               .first())
    if not gateman or gateman.revoked_at is not None:
        return unauthenticated('No active gateman for that phone on this event.')
    if not verify_password(pin, gateman.pin_hash):
        return unauthenticated('Wrong PIN.')

    now = datetime.now(timezone.utc)
    if gateman.locked_until is not None and gateman.locked_until < now:
        return unauthenticated('Session window has closed (event ended).')

    # Token expiry: 24h, but never longer than event.end_at + 24h.
    max_session = (event.end_at or now) + timedelta(hours=24)
    expires_in = min(timedelta(hours=24), max(timedelta(minutes=5), max_session - now))

    token = create_access_token(
        identity=str(gateman.id),
        expires_delta=expires_in,
        additional_claims={
            'gate_session': True,
            'gateman_id': str(gateman.id),
            'event_id': str(event.id),
        },
    )

    return jsonify({
        'token': token,
        'expires_in_seconds': int(expires_in.total_seconds()),
        'gateman': {
            'id': str(gateman.id),
            'name': gateman.name,
            'phone': gateman.phone,
            'scan_count': gateman.scan_count,
        },
        'event': {
            'id': str(event.id),
            'title': event.title,
            'start_at': event.start_at.isoformat() if event.start_at else None,
            'end_at': event.end_at.isoformat() if event.end_at else None,
            'location': event.location,
        },
    })


# ---------------------------------------------------------------------------
# Who am I (refresh session info)
# ---------------------------------------------------------------------------
@gate_bp.get('/me')
@gateman_required
def gate_me():
    gateman = g.gateman
    ev = gateman.event
    return jsonify({
        'gateman': {
            'id': str(gateman.id),
            'name': gateman.name,
            'phone': gateman.phone,
            'scan_count': gateman.scan_count,
        },
        'event': {
            'id': str(ev.id),
            'title': ev.title,
            'start_at': ev.start_at.isoformat() if ev.start_at else None,
            'end_at': ev.end_at.isoformat() if ev.end_at else None,
            'location': ev.location,
        },
    })


# ---------------------------------------------------------------------------
# Scan (the workhorse)
# ---------------------------------------------------------------------------
@gate_bp.post('/scan')
@gateman_required
def gate_scan():
    data = request.get_json(silent=True) or {}
    payload = (data.get('qr_payload') or data.get('qr_code') or '').strip()
    device_id = (data.get('device_id') or '').strip()[:100] or None
    scanned_at = (data.get('scanned_at') or '').strip() or None

    if not payload:
        return validation_failed('qr_payload is required.')

    try:
        result = scan_ticket(payload, g.gateman, device_id=device_id,
                             scanned_at_iso=scanned_at)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error during gate scan')
        return error_response('server_error', 'Scan failed.', 500)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Manifest (offline cache, optional)
# ---------------------------------------------------------------------------
@gate_bp.get('/event/<event_id>/manifest')
@gateman_required
def gate_manifest(event_id):
    """Full ticket list for offline caching. Scoped to gateman's event."""
    if str(event_id) != str(g.gateman.event_id):
        return error_response('forbidden',
                              'Gateman is not scoped to this event.',
                              403)
    rows = (db.session.query(Ticket)
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .filter(TicketType.event_id == event_id)
            .all())
    return jsonify({
        'event_id': event_id,
        'tickets': [
            {
                'id': str(t.id),
                'attendee_name': t.attendee_name,
                'status': t.status,
                'ticket_type': t.ticket_type.name if t.ticket_type else None,
            }
            for t in rows
        ],
    })
