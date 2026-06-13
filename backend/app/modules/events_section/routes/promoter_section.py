"""Promoter section endpoints — Stage 3 §5.2 / §5.3.

Sibling to TG's `promoter_admin.py`. This module owns:

  GET    /api/promoter/profile                          read promoter profile
  PUT    /api/promoter/profile                          update
  GET    /api/promoter/dashboard                        stats + recent activity
  POST   /api/promoter/events/flyer                     create flyer event
  PUT    /api/promoter/events/<id>                      edit flyer event (mode=flyer)
  POST   /api/promoter/events/<id>/convert-to-ticketed  flip flyer → ticketed
  POST   /api/promoter/uploads/image                    multipart image upload

TG owns the ticketed CRUD; this module owns the flyer-only paths plus the
generic profile/dashboard/upload surface.
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.models import PromoterProfile
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response, validation_failed, forbidden, not_found, conflict,
)

from app.modules.ticket_generator.models import (
    Event, TicketType, EVENT_CATEGORIES,
)
from app.modules.shop.uploads import upload_image_file, UploadError
from app.modules.purchase_interface.models import Purchase, PurchaseEvent


log = logging.getLogger('zimhub.events_section.promoter_section')

promoter_section_bp = Blueprint('events_section_promoter', __name__,
                                url_prefix='/api/promoter')


# ---------------------------------------------------------------------------
# Gates / helpers
# ---------------------------------------------------------------------------
def _require_promoter(user):
    if not user.is_promoter:
        return forbidden('You need a Promoter capability to access this.')
    return None


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


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@promoter_section_bp.get('/profile')
@require_auth
def get_profile(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    profile = user.promoter_profile
    if not profile:
        # Auto-vivify (defensive; should exist via approval).
        profile = PromoterProfile(user_id=user.id, default_currency='USD')
        db.session.add(profile)
        db.session.commit()
    return jsonify({'profile': profile.to_dict()})


@promoter_section_bp.put('/profile')
@require_auth
def update_profile(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    data = request.get_json(silent=True) or {}
    profile = user.promoter_profile
    if not profile:
        return not_found('Promoter profile missing.')
    if 'organisation_name' in data:
        profile.organisation_name = (data.get('organisation_name') or '').strip() or None
    if 'bio' in data:
        profile.bio = (data.get('bio') or '').strip() or None
    if 'photo_url' in data:
        profile.photo_url = (data.get('photo_url') or '').strip() or None
    db.session.commit()
    return jsonify({'profile': profile.to_dict()})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@promoter_section_bp.get('/dashboard')
@require_auth
def dashboard(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    now = datetime.now(timezone.utc)
    day_start = now - timedelta(hours=24)
    thirty_d = now - timedelta(days=30)

    upcoming_events = (Event.query
        .filter(Event.promoter_id == user.id,
                Event.status == 'active',
                Event.end_at >= now)
        .order_by(Event.start_at.asc()).limit(5).all())
    total_events = Event.query.filter(Event.promoter_id == user.id).count()

    pending_today = (Purchase.query
        .filter(Purchase.seller_id == user.id,
                Purchase.listing_type == 'event_ticket',
                Purchase.status == 'awaiting_payment',
                Purchase.created_at >= day_start)
        .count())

    # Tickets sold + revenue last 30d (completed event_ticket purchases).
    completed_rows = (Purchase.query
        .filter(Purchase.seller_id == user.id,
                Purchase.listing_type == 'event_ticket',
                Purchase.status == 'completed',
                Purchase.completed_at >= thirty_d)
        .all())
    tickets_sold_30d = sum(int(p.quantity or 0) for p in completed_rows)
    revenue_30d = sum((Decimal(str(p.total_usd or '0')) for p in completed_rows),
                      Decimal('0'))

    # Recent activity from this promoter's purchase events.
    recent_events = (db.session.query(PurchaseEvent, Purchase)
        .join(Purchase, PurchaseEvent.purchase_id == Purchase.id)
        .filter(Purchase.seller_id == user.id,
                Purchase.listing_type == 'event_ticket')
        .order_by(PurchaseEvent.created_at.desc())
        .limit(10).all())
    recent = []
    for ev, p in recent_events:
        recent.append({
            'purchase_id': str(p.id),
            'from_status': ev.from_status,
            'to_status': ev.to_status,
            'actor_role': ev.actor_role,
            'note': ev.note,
            'quantity': p.quantity,
            'total_usd': str(p.total_usd),
            'created_at': ev.created_at.isoformat() if ev.created_at else None,
        })

    return jsonify({
        'stats': {
            'upcoming_events': len(upcoming_events),
            'total_events': total_events,
            'tickets_sold_30d': tickets_sold_30d,
            'revenue_30d_usd': str(revenue_30d.quantize(Decimal('0.01'))),
            'today_pending_payments': pending_today,
        },
        'upcoming_events': [e.to_dict(include_ticket_types=False)
                            for e in upcoming_events],
        'recent_purchases': recent,
    })


# ---------------------------------------------------------------------------
# Flyer event create / edit / convert-to-ticketed
# ---------------------------------------------------------------------------
@promoter_section_bp.post('/events/flyer')
@require_auth
def create_flyer_event(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    data = request.get_json(silent=True) or {}
    field_errors = {}

    title = (data.get('title') or '').strip()
    if not title:
        field_errors['title'] = 'Required.'
    category = (data.get('category') or 'Other').strip()
    if category not in EVENT_CATEGORIES:
        field_errors['category'] = f'Must be one of: {", ".join(EVENT_CATEGORIES)}.'

    try:
        start_at = _parse_dt(data.get('start_at'))
        end_at = _parse_dt(data.get('end_at'))
    except ValueError as exc:
        field_errors['start_at'] = str(exc)
        start_at = end_at = None

    if not start_at:
        field_errors.setdefault('start_at', 'Required.')
    if not end_at:
        # Default end_at = start_at + 3h for flyer events (single-day social posts).
        end_at = (start_at + timedelta(hours=3)) if start_at else None

    if start_at and end_at and end_at < start_at:
        field_errors['end_at'] = 'Must be at or after start_at.'

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    e = Event(
        promoter_id=user.id,
        title=title[:200],
        description=(data.get('description') or '').strip(),
        category=category,
        start_at=start_at,
        end_at=end_at,
        location=(data.get('location') or '').strip()[:300],
        poster_url=(data.get('poster_url') or '').strip() or None,
        poster_thumb_url=(data.get('poster_url') or '').strip() or None,
        color_scheme=(data.get('color_scheme') or '').strip() or None,
        external_link=(data.get('external_link') or '').strip() or None,
        whatsapp_deep_link_text=(data.get('whatsapp_deep_link_text') or '').strip() or None,
        status='active',  # flyer events go live immediately (no payment flow).
        mode='flyer',
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)}), 201


@promoter_section_bp.put('/events/<event_id>')
@require_auth
def update_flyer_event(user, event_id):
    """Edit a flyer event in place. Ticketed edits go through TG's PATCH endpoint."""
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e = db.session.get(Event, event_id)
    if not e:
        return not_found('Event not found.')
    if str(e.promoter_id) != str(user.id):
        return forbidden('Not your event.')
    if e.mode != 'flyer':
        return error_response('wrong_mode',
                              'This endpoint edits flyer events. Use the ticketed PATCH endpoint for ticketed mode.',
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
    if 'external_link' in data:
        e.external_link = (data.get('external_link') or '').strip() or None
    if 'whatsapp_deep_link_text' in data:
        e.whatsapp_deep_link_text = (data.get('whatsapp_deep_link_text') or '').strip() or None
    try:
        if 'start_at' in data:
            e.start_at = _parse_dt(data.get('start_at'))
        if 'end_at' in data:
            e.end_at = _parse_dt(data.get('end_at'))
    except ValueError as exc:
        field_errors['start_at'] = str(exc)

    if e.start_at and e.end_at and e.end_at < e.start_at:
        field_errors['end_at'] = 'Must be at or after start_at.'
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)})


@promoter_section_bp.post('/events/<event_id>/convert-to-ticketed')
@require_auth
def convert_to_ticketed(user, event_id):
    """One-way convert flyer → ticketed (Stage 3 §5.3). Optionally seed types in one call."""
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    e = db.session.get(Event, event_id)
    if not e:
        return not_found('Event not found.')
    if str(e.promoter_id) != str(user.id):
        return forbidden('Not your event.')
    if e.mode != 'flyer':
        return conflict('Event is already ticketed.')

    data = request.get_json(silent=True) or {}
    types = data.get('ticket_types') or []
    if not isinstance(types, list):
        return validation_failed('ticket_types must be a list.')

    e.mode = 'ticketed'
    # Clear flyer-only fields.
    e.external_link = None
    e.whatsapp_deep_link_text = None

    for i, tt in enumerate(types):
        if not isinstance(tt, dict):
            continue
        name = (tt.get('name') or '').strip()
        if not name:
            continue
        try:
            price = Decimal(str(tt.get('price_usd', 0))).quantize(Decimal('0.01'))
        except Exception:
            price = Decimal('0.00')
        try:
            qty = int(tt.get('quantity_total', 0))
        except Exception:
            qty = 0
        db.session.add(TicketType(
            event_id=e.id, name=name[:120],
            description=(tt.get('description') or '').strip() or None,
            price_usd=price, quantity_total=max(0, qty),
        ))
    db.session.commit()
    return jsonify({'event': e.to_dict(include_ticket_types=True)})


# ---------------------------------------------------------------------------
# Image upload — reuses Stage 2's shop upload helper.
# ---------------------------------------------------------------------------
@promoter_section_bp.post('/uploads/image')
@require_auth
def upload_image(user):
    gate = _require_promoter(user)
    if gate is not None:
        return gate
    fs = request.files.get('file')
    if not fs:
        return validation_failed('file is required (multipart upload).')
    try:
        url = upload_image_file(fs)
    except UploadError as e:
        return error_response(e.code, e.message, e.status)
    except Exception:
        log.exception('Upload failed')
        return error_response('server_error', 'Could not upload image.', 500)
    return jsonify({'url': url})
