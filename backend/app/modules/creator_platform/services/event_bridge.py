"""Creator → TicketGenerator event bridge — Stage 5 §5.3.

A ticketed creator event IS a real TicketGenerator event owned by the creator.
We do NOT build a parallel ticketing system: this module creates genuine TG
`Event` / `TicketType` / `Gateman` rows with `promoter_id = creator.id`, so the
existing `event_ticket` PurchaseInterface handler, QR signing, gate scanning,
attendee CSV, and dispute desk all work unchanged.

Capability: a creator must be able to sell `event_ticket`s to own a TG event.
That is satisfied by the any-of `host.can_sell` change (§5.3): can_sell accepts
`is_promoter` OR `is_creator`. A pure buyer holds neither and is rejected here.
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation

from extensions import db
from app.services import host
from app.modules.ticket_generator.models import (
    Event, TicketType, EVENT_CATEGORIES,
)

log = logging.getLogger('zimhub.creator_platform.event_bridge')


class EventBridgeError(Exception):
    """Raised for validation / capability failures; carries a code + message."""
    def __init__(self, code, message, status=400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def assert_can_sell_tickets(user):
    """Gate: may this user own a ticketed (TG) event? Any-of promoter|creator."""
    if not host.can_sell(user, 'event_ticket'):
        raise EventBridgeError(
            'forbidden',
            'You need a Creator or Promoter capability to sell tickets.',
            403,
        )


def _parse_price(v):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError):
        raise EventBridgeError('validation_failed', 'price_usd must be a valid amount.')
    if d < 0:
        raise EventBridgeError('validation_failed', 'price_usd must be >= 0.')
    return d.quantize(Decimal('0.01'))


def _parse_qty(v):
    try:
        i = int(v)
    except (ValueError, TypeError):
        raise EventBridgeError('validation_failed', 'quantity_total must be an integer.')
    if i < 0:
        raise EventBridgeError('validation_failed', 'quantity_total must be >= 0.')
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
        raise EventBridgeError('validation_failed', 'Invalid datetime; use ISO 8601.')


def create_ticketed_tg_event(creator_user, data: dict) -> Event:
    """Create a real TicketGenerator event owned by the creator.

    Returns the persisted (flushed) Event with its ticket types. Caller commits.
    The creator is the TG `promoter_id` — making them the seller for the
    `event_ticket` PurchaseInterface flow, exactly like a Promoter event.
    """
    assert_can_sell_tickets(creator_user)

    title = (data.get('title') or '').strip()
    if not title:
        raise EventBridgeError('validation_failed', 'Title is required.')
    description = (data.get('description') or '').strip()
    category = (data.get('category') or '').strip() or 'Arts & Culture'
    if category not in EVENT_CATEGORIES:
        category = 'Arts & Culture'
    location = (data.get('location') or data.get('venue_name') or '').strip()
    poster_url = (data.get('poster_url') or '').strip() or None

    start_at = _parse_dt(data.get('start_at') or data.get('event_date'))
    end_at = _parse_dt(data.get('end_at'))
    if not start_at:
        raise EventBridgeError('validation_failed', 'start_at (event date) is required.')
    if not end_at:
        end_at = start_at + timedelta(hours=4)  # sensible default duration
    if end_at <= start_at:
        raise EventBridgeError('validation_failed', 'end_at must be after start_at.')

    ticket_types_in = data.get('ticket_types') or []
    if not isinstance(ticket_types_in, list) or not ticket_types_in:
        raise EventBridgeError(
            'validation_failed',
            'A ticketed event needs at least one ticket type.',
        )

    # Honour the same EVENT_MODERATION switch promoters obey.
    moderation_on = bool(host.config('EVENT_MODERATION', False))
    status = 'pending_approval' if moderation_on else 'active'

    ev = Event(
        promoter_id=creator_user.id,   # <-- the creator owns the TG event
        title=title[:200],
        description=description,
        category=category,
        start_at=start_at,
        end_at=end_at,
        location=location[:300],
        poster_url=poster_url,
        poster_thumb_url=poster_url,
        status=status,
        mode='ticketed',
    )
    db.session.add(ev)
    db.session.flush()

    for tt in ticket_types_in:
        if not isinstance(tt, dict):
            continue
        name = (tt.get('name') or '').strip()
        if not name:
            raise EventBridgeError('validation_failed', 'Each ticket type needs a name.')
        db.session.add(TicketType(
            event_id=ev.id,
            name=name[:120],
            description=(tt.get('description') or '').strip() or None,
            price_usd=_parse_price(tt.get('price_usd', 0)),
            quantity_total=_parse_qty(tt.get('quantity_total', 0)),
        ))

    db.session.flush()
    log.info('[CREATOR→TG] event=%s owner(creator)=%s title=%r types=%d',
             ev.id, creator_user.id, ev.title, len(ticket_types_in))
    return ev


def load_creator_tg_event(creator_user, event_id):
    """Load a TG event and assert the creator owns it. Returns Event or None."""
    ev = db.session.get(Event, event_id)
    if ev is None:
        return None
    if str(ev.promoter_id) != str(creator_user.id):
        return None
    return ev
