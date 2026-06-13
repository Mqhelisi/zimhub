"""Promoter admin endpoints — per TG spec §9 + Stage 3 §6.4.

Scope:
  GET    /api/promoter/events                              own events list
  POST   /api/promoter/events                              create ticketed event
  GET    /api/promoter/events/:id                          own event detail
  PATCH  /api/promoter/events/:id                          edit ticketed event
  POST   /api/promoter/events/:id/publish                  → active (or pending_approval)
  POST   /api/promoter/events/:id/cancel                   voids tickets, refund path
  POST   /api/promoter/events/:id/ticket-types             add ticket type
  PATCH  /api/promoter/ticket-types/:id                    edit ticket type
  DELETE /api/promoter/ticket-types/:id                    delete (only if 0 sold/held)

  GET    /api/promoter/events/:id/attendees                list + summary
  GET    /api/promoter/events/:id/attendees.csv            CSV download

  GET    /api/promoter/events/:id/gatemen                  list
  POST   /api/promoter/events/:id/gatemen                  create
  POST   /api/promoter/gatemen/:id/regenerate-pin          new PIN
  DELETE /api/promoter/gatemen/:id                         revoke

Flyer events: edits/creates go through events_section's /api/promoter/events/flyer.
"""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify, Response
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response, validation_failed, forbidden, not_found, conflict,
)
from app.utils.passwords import hash_password
from app.services import host

from ..models import (
    Event, TicketType, Ticket, Gateman,
    EVENT_CATEGORIES, EVENT_STATUSES,
)
from ..services.csv_export import attendees_csv, csv_filename


log = logging.getLogger('zimhub.ticket_generator.promoter_admin')

promoter_admin_bp = Blueprint('tg_promoter_admin', __name__, url_prefix='/api/promoter')


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def _require_promoter(user):
    if not user.is_promoter:
        return forbidden('You need a Promoter capability to access this.')
    return None


def _load_own_event(user, event_id):
    e = db.session.get(Event, event_id)
    if not e:
        return None, not_found('Event not found.')
    if str(e.promoter_id) != str(user.id):
        return None, forbidden('Not your event.')
    return e, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_price(v):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError):
        raise ValueError('price_usd must be a valid amount.')
    if d < 0:
        raise ValueError('price_usd must be >= 0.')
    return d.quantize(Decimal('0.01'))


def _parse_qty(v, *, field='quantity'):
    try:
        i = int(v)
    except (ValueError, TypeError):
        raise ValueError(f'{field} must be an integer.')
    if i < 0:
        raise ValueError(f'{field} must be >= 0.')
    return i


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
        raise ValueError('Invalid datetime; use ISO 8601.')


def _gen_pin():
    return ''.join(secrets.choice('0123456789') for _ in range(4))


# ---------------------------------------------------------------------------
# Events list / create (ticketed)
# ---------------------------------------------------------------------------
@promoter_admin_bp.get('/events')
@require_auth
def list_own_events(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    status = (request.args.get('status') or '').strip().lower()
    mode = (request.args.get('mode') or '').strip().lower()
    timing = (request.args.get('timing') or '').strip().lower()  # upcoming|past
    q = Event.query.filter(Event.promoter_id == user.id)
    if status in EVENT_STATUSES:
        q = q.filter(Event.status == status)
    if mode in ('ticketed', 'flyer'):
        q = q.filter(Event.mode == mode)
    now = datetime.now(timezone.utc)
    if timing == 'upcoming':
        q = q.filter(Event.end_at >= now)
    elif timing == 'past':
        q = q.filter(Event.end_at < now)
    rows = q.order_by(Event.start_at.desc()).limit(200).all()
    return jsonify({'events': [e.to_dict(include_ticket_types=True) for e in rows]})


@promoter_admin_bp.post('/events')
@require_auth
def create_ticketed_event(user):
    """Create a ticketed event. Flyer creation lives in events_section."""
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    data = request.get_json(silent=True) or {}
    field_errors = {}

    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    category = (data.get('category') or '').strip()
    location = (data.get('location') or '').strip()
    poster_url = (data.get('poster_url') or '').strip() or None
    color_scheme = (data.get('color_scheme') or '').strip() or None
    status = (data.get('status') or 'draft').strip().lower()

    if not title:
        field_errors['title'] = 'Required.'
    if category and category not in EVENT_CATEGORIES:
        field_errors['category'] = f'Must be one of: {", ".join(EVENT_CATEGORIES)}.'
    if not category:
        category = 'Other'

    if status not in ('draft', 'active'):
        field_errors['status'] = 'Must be draft or active on create.'

    try:
        start_at = _parse_dt(data.get('start_at'))
        end_at = _parse_dt(data.get('end_at'))
    except ValueError as e:
        field_errors['start_at'] = str(e)
        start_at = end_at = None

    if not start_at:
        field_errors.setdefault('start_at', 'Required.')
    if not end_at:
        field_errors.setdefault('end_at', 'Required.')
    if start_at and end_at and end_at <= start_at:
        field_errors['end_at'] = 'Must be after start_at.'

    ticket_types_in = data.get('ticket_types') or []
    if not isinstance(ticket_types_in, list):
        field_errors['ticket_types'] = 'Must be a list.'
        ticket_types_in = []

    for i, tt in enumerate(ticket_types_in):
        if not isinstance(tt, dict):
            field_errors[f'ticket_types[{i}]'] = 'Must be an object.'
            continue
        if not (tt.get('name') or '').strip():
            field_errors[f'ticket_types[{i}].name'] = 'Required.'
        try:
            _parse_price(tt.get('price_usd', 0))
        except ValueError as e:
            field_errors[f'ticket_types[{i}].price_usd'] = str(e)
        try:
            _parse_qty(tt.get('quantity_total', 0))
        except ValueError as e:
            field_errors[f'ticket_types[{i}].quantity_total'] = str(e)

    if status == 'active' and not ticket_types_in:
        field_errors['ticket_types'] = 'At least one ticket type is required for an active event.'

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    moderation_on = bool(host.config('EVENT_MODERATION', False))
    final_status = status
    if status == 'active' and moderation_on:
        final_status = 'pending_approval'

    e = Event(
        promoter_id=user.id,
        title=title[:200],
        description=description,
        category=category,
        start_at=start_at,
        end_at=end_at,
        location=location[:300],
        poster_url=poster_url,
        poster_thumb_url=poster_url,
        color_scheme=color_scheme,
        status=final_status,
        mode='ticketed',
    )
    db.session.add(e)
    db.session.flush()

    for tt in ticket_types_in:
        db.session.add(TicketType(
            event_id=e.id,
            name=(tt.get('name') or '').strip()[:120],
            description=(tt.get('description') or '').strip() or None,
            price_usd=_parse_price(tt.get('price_usd', 0)),
            quantity_total=_parse_qty(tt.get('quantity_total', 0)),
        ))

    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)}), 201


# ---------------------------------------------------------------------------
# Event detail / edit
# ---------------------------------------------------------------------------
@promoter_admin_bp.get('/events/<event_id>')
@require_auth
def get_own_event(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    return jsonify({'event': e.to_dict(include_ticket_types=True)})


@promoter_admin_bp.patch('/events/<event_id>')
@require_auth
def edit_own_event(user, event_id):
    """Edit a ticketed event in place. Flyer events use the events_section endpoint."""
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    if e.mode != 'ticketed':
        return error_response('wrong_mode',
                              'This endpoint edits ticketed events; use the flyer endpoint for flyer mode.',
                              400)

    data = request.get_json(silent=True) or {}
    field_errors = {}

    if 'title' in data:
        v = (data.get('title') or '').strip()
        if not v:
            field_errors['title'] = 'Required.'
        else:
            e.title = v[:200]
    if 'description' in data:
        e.description = (data.get('description') or '').strip()
    if 'category' in data:
        cat = (data.get('category') or '').strip()
        if cat not in EVENT_CATEGORIES:
            field_errors['category'] = f'Must be one of: {", ".join(EVENT_CATEGORIES)}.'
        else:
            e.category = cat
    if 'location' in data:
        e.location = (data.get('location') or '').strip()[:300]
    if 'poster_url' in data:
        url = (data.get('poster_url') or '').strip() or None
        e.poster_url = url
        e.poster_thumb_url = url
    if 'color_scheme' in data:
        e.color_scheme = (data.get('color_scheme') or '').strip() or None
    try:
        if 'start_at' in data:
            e.start_at = _parse_dt(data.get('start_at'))
        if 'end_at' in data:
            e.end_at = _parse_dt(data.get('end_at'))
    except ValueError as exc:
        field_errors['start_at'] = str(exc)
    if e.start_at and e.end_at and e.end_at <= e.start_at:
        field_errors['end_at'] = 'Must be after start_at.'

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)})


@promoter_admin_bp.post('/events/<event_id>/publish')
@require_auth
def publish_event(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    if e.status not in ('draft', 'rejected'):
        return conflict(f"Cannot publish from status={e.status}.")
    if e.mode == 'ticketed' and not e.ticket_types:
        return conflict('Ticketed events need at least one ticket type before publish.')
    moderation_on = bool(host.config('EVENT_MODERATION', False))
    e.status = 'pending_approval' if moderation_on else 'active'
    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)})


# ---------------------------------------------------------------------------
# Cancel event — voids valid tickets, fires refund/dispute notifications.
# ---------------------------------------------------------------------------
@promoter_admin_bp.post('/events/<event_id>/cancel')
@require_auth
def cancel_event(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    if e.status in ('cancelled', 'archived'):
        return conflict(f"Event already {e.status}.")

    e.status = 'cancelled'

    # Void all currently-valid tickets, notify their buyers.
    valid_tickets = (db.session.query(Ticket)
                                .join(TicketType, Ticket.ticket_type_id == TicketType.id)
                                .filter(TicketType.event_id == e.id,
                                        Ticket.status == 'valid')
                                .all())
    voided_count = 0
    for t in valid_tickets:
        t.status = 'voided'
        voided_count += 1
        if t.purchase and t.purchase.buyer:
            host.notify(
                t.purchase.buyer_id, 'event_cancelled',
                f"Event cancelled: {e.title}",
                f"The event has been cancelled. Your ticket is voided. "
                f"For refunds, coordinate with the promoter or open a dispute "
                f"from your purchase page.",
                metadata={
                    'event_id': str(e.id),
                    'ticket_id': str(t.id),
                    'purchase_id': str(t.purchase_id) if t.purchase_id else None,
                },
            )
            host.send(
                channel='whatsapp', recipient=t.purchase.buyer.phone,
                body=f"ZimHub: {e.title} has been cancelled. Your ticket is voided. "
                     f"Open your purchase to coordinate a refund or open a dispute.",
            )

    db.session.commit()
    return jsonify({
        'event': e.to_dict(include_ticket_types=True),
        'voided_tickets': voided_count,
    })


# ---------------------------------------------------------------------------
# Ticket types
# ---------------------------------------------------------------------------
@promoter_admin_bp.post('/events/<event_id>/ticket-types')
@require_auth
def add_ticket_type(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    if e.mode != 'ticketed':
        return error_response('wrong_mode',
                              'Cannot add ticket types to a flyer event. Convert it first.',
                              400)
    data = request.get_json(silent=True) or {}
    field_errors = {}
    name = (data.get('name') or '').strip()
    if not name:
        field_errors['name'] = 'Required.'
    try:
        price = _parse_price(data.get('price_usd', 0))
    except ValueError as exc:
        field_errors['price_usd'] = str(exc)
        price = None
    try:
        qty = _parse_qty(data.get('quantity_total', 0))
    except ValueError as exc:
        field_errors['quantity_total'] = str(exc)
        qty = None
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    tt = TicketType(
        event_id=e.id, name=name[:120],
        description=(data.get('description') or '').strip() or None,
        price_usd=price, quantity_total=qty,
    )
    db.session.add(tt)
    db.session.commit()
    return jsonify({'ticket_type': tt.to_dict()}), 201


@promoter_admin_bp.patch('/ticket-types/<tt_id>')
@require_auth
def edit_ticket_type(user, tt_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    tt = db.session.get(TicketType, tt_id)
    if not tt:
        return not_found('Ticket type not found.')
    if str(tt.event.promoter_id) != str(user.id):
        return forbidden('Not your event.')

    data = request.get_json(silent=True) or {}
    field_errors = {}
    if 'name' in data:
        v = (data.get('name') or '').strip()
        if v:
            tt.name = v[:120]
    if 'description' in data:
        tt.description = (data.get('description') or '').strip() or None
    if 'price_usd' in data:
        try:
            new_price = _parse_price(data.get('price_usd'))
        except ValueError as exc:
            field_errors['price_usd'] = str(exc)
        else:
            tt.price_usd = new_price
    if 'quantity_total' in data:
        try:
            new_qty = _parse_qty(data.get('quantity_total'))
        except ValueError as exc:
            field_errors['quantity_total'] = str(exc)
        else:
            reserved = (tt.quantity_held or 0) + (tt.quantity_sold or 0)
            if new_qty < reserved:
                field_errors['quantity_total'] = (
                    f'Cannot be less than held + sold ({reserved}).'
                )
            else:
                tt.quantity_total = new_qty
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)
    db.session.commit()
    return jsonify({'ticket_type': tt.to_dict()})


@promoter_admin_bp.delete('/ticket-types/<tt_id>')
@require_auth
def delete_ticket_type(user, tt_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    tt = db.session.get(TicketType, tt_id)
    if not tt:
        return not_found('Ticket type not found.')
    if str(tt.event.promoter_id) != str(user.id):
        return forbidden('Not your event.')
    if (tt.quantity_sold or 0) > 0 or (tt.quantity_held or 0) > 0:
        return conflict('Cannot delete — tickets are sold or held.')
    db.session.delete(tt)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Attendees + CSV export
# ---------------------------------------------------------------------------
@promoter_admin_bp.get('/events/<event_id>/attendees')
@require_auth
def event_attendees(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    rows = (db.session.query(Ticket)
            .join(TicketType, Ticket.ticket_type_id == TicketType.id)
            .filter(TicketType.event_id == e.id)
            .order_by(Ticket.created_at.asc()).all())
    summary = {
        'total': len(rows),
        'checked_in': sum(1 for r in rows if r.status == 'used'),
        'online': sum(1 for r in rows if r.source == 'online'),
        'walk_in': sum(1 for r in rows if r.source == 'walk_in'),
        'comp': sum(1 for r in rows if r.source == 'comp'),
        'voided': sum(1 for r in rows if r.status == 'voided'),
    }
    return jsonify({
        'event': e.to_dict(include_ticket_types=True),
        'attendees': [t.attendees_row() for t in rows],
        'summary': summary,
    })


@promoter_admin_bp.get('/events/<event_id>/attendees.csv')
@require_auth
def event_attendees_csv(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    scope = (request.args.get('scope') or 'all').strip().lower()
    if scope not in ('all', 'checked_in'):
        scope = 'all'
    body = attendees_csv(e, scope=scope)
    filename = csv_filename(e, scope=scope)
    return Response(
        body,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Gatemen
# ---------------------------------------------------------------------------
@promoter_admin_bp.get('/events/<event_id>/gatemen')
@require_auth
def list_gatemen(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err
    rows = Gateman.query.filter(Gateman.event_id == e.id,
                                Gateman.revoked_at.is_(None)).all()
    return jsonify({'gatemen': [g.to_dict() for g in rows]})


@promoter_admin_bp.post('/events/<event_id>/gatemen')
@require_auth
def create_gateman(user, event_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e, err = _load_own_event(user, event_id)
    if err:
        return err

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
    active_count = Gateman.query.filter(
        Gateman.event_id == e.id, Gateman.revoked_at.is_(None),
    ).count()
    if active_count >= cap:
        return conflict(f'Already at the cap of {cap} active gatemen for this event.')

    # Check phone uniqueness on this event.
    existing = Gateman.query.filter(
        Gateman.event_id == e.id, Gateman.phone == phone,
        Gateman.revoked_at.is_(None),
    ).first()
    if existing:
        return conflict('A gateman with this phone is already active on this event.')

    locked_until = (e.end_at or datetime.now(timezone.utc)) + timedelta(hours=24)
    gm = Gateman(
        event_id=e.id, name=name[:120], phone=phone[:20],
        pin_hash=hash_password(pin),
        locked_until=locked_until,
        created_by=user.id,
    )
    db.session.add(gm)
    db.session.commit()
    out = gm.to_dict()
    out['pin'] = pin  # ONE-TIME echo for handoff.
    return jsonify({'gateman': out}), 201


@promoter_admin_bp.post('/gatemen/<gateman_id>/regenerate-pin')
@require_auth
def regenerate_pin(user, gateman_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    gm = db.session.get(Gateman, gateman_id)
    if not gm:
        return not_found('Gateman not found.')
    if str(gm.event.promoter_id) != str(user.id):
        return forbidden('Not your event.')
    pin = _gen_pin()
    gm.pin_hash = hash_password(pin)
    db.session.commit()
    out = gm.to_dict()
    out['pin'] = pin
    return jsonify({'gateman': out})


@promoter_admin_bp.delete('/gatemen/<gateman_id>')
@require_auth
def revoke_gateman(user, gateman_id):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    gm = db.session.get(Gateman, gateman_id)
    if not gm:
        return not_found('Gateman not found.')
    if str(gm.event.promoter_id) != str(user.id):
        return forbidden('Not your event.')
    gm.revoked_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Categories enum
# ---------------------------------------------------------------------------
@promoter_admin_bp.get('/event-categories')
@require_auth
def event_categories(user):
    return jsonify({'categories': list(EVENT_CATEGORIES)})
