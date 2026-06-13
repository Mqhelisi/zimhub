"""Creator events routes — CreatorPlatform_Spec.md §5.4 + Stage 5 §5.3.
Auth + is_creator. Dual-mode:

  - Ticketed (host_ticketing): bridges to a REAL TicketGenerator event owned by
    the creator (event_bridge). Reuses TG ticket types, gatemen, attendees, QR,
    gate scanning, and the event_ticket PurchaseInterface flow — no parallel
    ticketing. The creator's selling capability comes from the any-of can_sell
    change (is_promoter OR is_creator).
  - External/free: a native CreatorEvent row (no TG, no tickets).

  GET    /api/creator/events                          own events (both modes)
  POST   /api/creator/events                          create (mode-aware)
  GET    /api/creator/events/:id                      detail (+ host_event)
  PATCH  /api/creator/events/:id                      edit native fields
  DELETE /api/creator/events/:id                      delete (cancels TG event if ticketed)

  -- ticketed-only management on the creator's own TG event (ownership-scoped) --
  POST   /api/creator/events/:id/ticket-types         add a TG ticket type
  GET    /api/creator/events/:id/gatemen              list gatemen
  POST   /api/creator/events/:id/gatemen              create a gateman (PIN echoed once)
  GET    /api/creator/events/:id/attendees            attendees + summary
"""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import forbidden, validation_failed, not_found, conflict, error_response
from app.utils.passwords import hash_password
from app.services import host

from ..models import CreatorEvent, CREATOR_EVENT_MODES
from ..services.event_bridge import (
    create_ticketed_tg_event, load_creator_tg_event, EventBridgeError,
)
from app.modules.ticket_generator.models import Event, TicketType, Ticket, Gateman

log = logging.getLogger('zimhub.creator_platform.events')

creator_events_bp = Blueprint('creator_platform_events', __name__,
                              url_prefix='/api/creator/events')


def _require_creator(user):
    if not user.is_creator:
        return None, forbidden('You need a Creator capability to access this.')
    if user.creator_profile is None:
        return None, forbidden('Your creator profile is not provisioned yet.')
    return user.creator_profile, None


def _load_own_creator_event(profile, ce_id):
    ce = db.session.get(CreatorEvent, ce_id)
    if not ce:
        return None, not_found('Event not found.')
    if str(ce.creator_id) != str(profile.user_id):
        return None, forbidden('Not your event.')
    return ce, None


def _parse_dt(s):
    if not s:
        return None
    try:
        if isinstance(s, str) and s.endswith('Z'):
            s = s[:-1] + '+00:00'
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def _gen_pin():
    return ''.join(secrets.choice('0123456789') for _ in range(4))


# ---------------------------------------------------------------------------
# List / create
# ---------------------------------------------------------------------------
@creator_events_bp.get('')
@creator_events_bp.get('/')
@require_auth
def list_events(user):
    profile, err = _require_creator(user)
    if err:
        return err
    rows = (CreatorEvent.query
            .filter(CreatorEvent.creator_id == profile.user_id)
            .order_by(CreatorEvent.event_date.asc()).all())
    return jsonify({'events': [e.to_dict(include_host_event=True) for e in rows]})


@creator_events_bp.post('')
@creator_events_bp.post('/')
@require_auth
def create_event(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    mode = (data.get('ticketing_mode') or '').strip()
    if mode not in CREATOR_EVENT_MODES:
        return validation_failed('Some fields are invalid.',
                                 field_errors={'ticketing_mode':
                                               f'Must be one of: {", ".join(CREATOR_EVENT_MODES)}.'})

    title = (data.get('title') or '').strip()
    event_date = _parse_dt(data.get('event_date') or data.get('start_at'))
    field_errors = {}
    if not title:
        field_errors['title'] = 'Required.'
    if not event_date:
        field_errors['event_date'] = 'Valid event date is required.'
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    host_event_id = None
    if mode == 'host_ticketing':
        # Build a REAL TicketGenerator event owned by the creator.
        try:
            tg_event = create_ticketed_tg_event(user, {
                'title': title,
                'description': data.get('description'),
                'category': data.get('category'),
                'location': data.get('venue_name') or data.get('location'),
                'poster_url': data.get('poster_url'),
                'start_at': data.get('event_date') or data.get('start_at'),
                'end_at': data.get('end_at'),
                'ticket_types': data.get('ticket_types') or [],
            })
        except EventBridgeError as e:
            db.session.rollback()
            return error_response(e.code, e.message, e.status)
        host_event_id = tg_event.id
    else:
        # External / free — validate the off-platform fields.
        price = (data.get('ticket_price') or '').strip() or None
        ext_url = (data.get('external_ticket_url') or '').strip() or None
        if not price and not ext_url:
            # default to free if neither given
            price = 'free'

    ce = CreatorEvent(
        creator_id=profile.user_id,
        submitted_by=user.id,
        title=title[:200],
        description=(data.get('description') or '').strip() or None,
        event_date=event_date,
        venue_name=(data.get('venue_name') or '').strip() or None,
        google_maps_url=(data.get('google_maps_url') or '').strip() or None,
        poster_url=(data.get('poster_url') or '').strip() or None,
        ticketing_mode=mode,
        host_event_id=host_event_id,
        ticket_price=(data.get('ticket_price') or ('free' if mode == 'external' else None)),
        external_ticket_url=(data.get('external_ticket_url') or '').strip() or None,
        status='approved',  # post-moderation (Stage 5 §11) — publishes immediately
    )
    db.session.add(ce)
    db.session.commit()
    return jsonify({'event': ce.to_dict(include_host_event=True)}), 201


@creator_events_bp.get('/<ce_id>')
@require_auth
def get_event(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, cerr = _load_own_creator_event(profile, ce_id)
    if cerr:
        return cerr
    return jsonify({'event': ce.to_dict(include_host_event=True)})


@creator_events_bp.patch('/<ce_id>')
@require_auth
def edit_event(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, cerr = _load_own_creator_event(profile, ce_id)
    if cerr:
        return cerr
    data = request.get_json(silent=True) or {}
    if 'title' in data:
        v = (data.get('title') or '').strip()
        if v:
            ce.title = v[:200]
    if 'description' in data:
        ce.description = (data.get('description') or '').strip() or None
    if 'venue_name' in data:
        ce.venue_name = (data.get('venue_name') or '').strip() or None
    if 'google_maps_url' in data:
        ce.google_maps_url = (data.get('google_maps_url') or '').strip() or None
    if 'event_date' in data:
        d = _parse_dt(data.get('event_date'))
        if d:
            ce.event_date = d
    if ce.ticketing_mode == 'external':
        if 'ticket_price' in data:
            ce.ticket_price = (data.get('ticket_price') or '').strip() or None
        if 'external_ticket_url' in data:
            ce.external_ticket_url = (data.get('external_ticket_url') or '').strip() or None
    # Keep the linked TG event's headline fields in sync for ticketed events.
    if ce.ticketing_mode == 'host_ticketing' and ce.host_event_id:
        ev = db.session.get(Event, ce.host_event_id)
        if ev:
            ev.title = ce.title
            if ce.description is not None:
                ev.description = ce.description
            if ce.venue_name:
                ev.location = ce.venue_name
    db.session.commit()
    return jsonify({'event': ce.to_dict(include_host_event=True)})


@creator_events_bp.delete('/<ce_id>')
@require_auth
def delete_event(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, cerr = _load_own_creator_event(profile, ce_id)
    if cerr:
        return cerr
    # Ticketed: cancel the TG event (voids valid tickets) rather than hard-delete.
    if ce.ticketing_mode == 'host_ticketing' and ce.host_event_id:
        ev = db.session.get(Event, ce.host_event_id)
        if ev and ev.status not in ('cancelled', 'archived'):
            ev.status = 'cancelled'
            valid = (db.session.query(Ticket)
                     .join(TicketType, Ticket.ticket_type_id == TicketType.id)
                     .filter(TicketType.event_id == ev.id, Ticket.status == 'valid')
                     .all())
            for t in valid:
                t.status = 'voided'
    db.session.delete(ce)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Ticketed-only: ticket types on the creator's own TG event
# ---------------------------------------------------------------------------
def _load_ticketed_tg_event(user, ce_id):
    """Resolve a creator event id → its owned TG Event, or (None, error)."""
    ce = db.session.get(CreatorEvent, ce_id)
    if not ce or str(ce.creator_id) != str(user.id):
        return None, None, not_found('Event not found.')
    if ce.ticketing_mode != 'host_ticketing' or not ce.host_event_id:
        return None, None, conflict('This event is not a ticketed event.')
    ev = load_creator_tg_event(user, ce.host_event_id)
    if ev is None:
        return None, None, not_found('Linked ticketed event not found.')
    return ce, ev, None


@creator_events_bp.post('/<ce_id>/ticket-types')
@require_auth
def add_ticket_type(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, ev, terr = _load_ticketed_tg_event(user, ce_id)
    if terr:
        return terr
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return validation_failed('Some fields are invalid.',
                                 field_errors={'name': 'Required.'})
    try:
        price = Decimal(str(data.get('price_usd', 0))).quantize(Decimal('0.01'))
        qty = int(data.get('quantity_total', 0))
        if price < 0 or qty < 0:
            raise ValueError
    except Exception:
        return validation_failed('Price and quantity must be valid.')
    tt = TicketType(event_id=ev.id, name=name[:120],
                    description=(data.get('description') or '').strip() or None,
                    price_usd=price, quantity_total=qty)
    db.session.add(tt)
    db.session.commit()
    return jsonify({'ticket_type': tt.to_dict()}), 201


# ---------------------------------------------------------------------------
# Ticketed-only: gatemen on the creator's own TG event
# ---------------------------------------------------------------------------
@creator_events_bp.get('/<ce_id>/gatemen')
@require_auth
def list_gatemen(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, ev, terr = _load_ticketed_tg_event(user, ce_id)
    if terr:
        return terr
    rows = Gateman.query.filter(Gateman.event_id == ev.id,
                                Gateman.revoked_at.is_(None)).all()
    return jsonify({'gatemen': [g.to_dict() for g in rows]})


@creator_events_bp.post('/<ce_id>/gatemen')
@require_auth
def create_gateman(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, ev, terr = _load_ticketed_tg_event(user, ce_id)
    if terr:
        return terr
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    pin = (data.get('pin') or '').strip() or _gen_pin()
    field_errors = {}
    if not name:
        field_errors['name'] = 'Required.'
    if not phone:
        field_errors['phone'] = 'Required.'
    if pin and (not pin.isdigit() or len(pin) != 4):
        field_errors['pin'] = 'PIN must be exactly 4 digits.'
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    cap = int(host.config('GATEMEN_PER_EVENT', 2) or 2)
    active = Gateman.query.filter(Gateman.event_id == ev.id,
                                  Gateman.revoked_at.is_(None)).count()
    if active >= cap:
        return conflict(f'Already at the cap of {cap} active gatemen for this event.')
    existing = Gateman.query.filter(Gateman.event_id == ev.id,
                                    Gateman.phone == phone,
                                    Gateman.revoked_at.is_(None)).first()
    if existing:
        return conflict('A gateman with this phone is already active on this event.')

    locked_until = (ev.end_at or datetime.now(timezone.utc)) + timedelta(hours=24)
    gm = Gateman(event_id=ev.id, name=name[:120], phone=phone[:20],
                 pin_hash=hash_password(pin), locked_until=locked_until,
                 created_by=user.id)
    db.session.add(gm)
    db.session.commit()
    out = gm.to_dict()
    out['pin'] = pin  # one-time echo for handoff
    return jsonify({'gateman': out}), 201


# ---------------------------------------------------------------------------
# Ticketed-only: attendees + summary
# ---------------------------------------------------------------------------
@creator_events_bp.get('/<ce_id>/attendees')
@require_auth
def attendees(user, ce_id):
    profile, err = _require_creator(user)
    if err:
        return err
    ce, ev, terr = _load_ticketed_tg_event(user, ce_id)
    if terr:
        return terr
    rows = (db.session.query(Ticket)
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .filter(TicketType.event_id == ev.id)
            .order_by(Ticket.created_at.asc()).all())
    summary = {
        'total': len(rows),
        'checked_in': sum(1 for r in rows if r.status == 'used'),
        'voided': sum(1 for r in rows if r.status == 'voided'),
    }
    return jsonify({
        'event': ev.to_dict(include_ticket_types=True),
        'attendees': [t.attendees_row() for t in rows],
        'summary': summary,
    })
