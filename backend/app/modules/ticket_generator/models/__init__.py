"""TicketGenerator models — per TICKET_GENERATOR_SPEC.md §8 + Stage 3 §5.3.

Tables owned here:
    events           — promoter-owned event (ticketed OR flyer per Stage 3 ext)
    ticket_types     — the Listing for event_ticket (one event → many types)
    tickets          — the delivered good (HMAC-signed QR)
    gatemen          — phone+PIN credentials, scoped to one event
    checkins         — immutable scan log

NOT owned here:
    purchases, purchase_events, disputes  — live in PurchaseInterface.
    tickets link back via purchase_id (nullable: comp / walk-in mints).
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, ForeignKey,
    CheckConstraint, Index, UniqueConstraint, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# Status enums (validated at route layer; stored as strings for portability)
EVENT_STATUSES = (
    'draft', 'pending_approval', 'active', 'rejected', 'cancelled', 'archived',
)
EVENT_CATEGORIES = (
    'Music', 'Church', 'Arts & Culture', 'Festival', 'Sports', 'Comedy',
    'Conference', 'Other',
)
EVENT_MODES = ('ticketed', 'flyer')
TICKET_STATUSES = ('valid', 'used', 'voided')
TICKET_SOURCES = ('online', 'walk_in', 'comp')
CHECKIN_RESULTS = ('success', 'duplicate', 'invalid')


# ---------------------------------------------------------------------------
# Event — TG-owned, extended by Stage 3 with the `mode` + flyer-only columns
# (Stage 3 §5.3). Since this is a single Stage-3 migration, we just include
# them on the model directly.
# ---------------------------------------------------------------------------
class Event(db.Model):
    __tablename__ = 'events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    promoter_id = Column(UUID(as_uuid=True), ForeignKey('users.id'),
                         nullable=False, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default='')
    category = Column(String(40), nullable=False, default='Other')

    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(300), nullable=False, default='')

    # Visuals
    poster_url = Column(String(500), nullable=True)
    poster_thumb_url = Column(String(500), nullable=True)
    color_scheme = Column(String(40), nullable=True)  # "#xxxxxx,#xxxxxx"

    # Status
    status = Column(String(20), nullable=False, default='draft', index=True)
    rejection_reason = Column(Text, nullable=True)

    # Stage 3 §5.3 — flyer extension. mode is ALWAYS present.
    mode = Column(String(20), nullable=False, default='ticketed')
    external_link = Column(String(500), nullable=True)            # flyer-only
    whatsapp_deep_link_text = Column(Text, nullable=True)         # flyer-only

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=utcnow, onupdate=utcnow)

    promoter = relationship('User', foreign_keys=[promoter_id])
    ticket_types = relationship(
        'TicketType', back_populates='event', cascade='all, delete-orphan',
        order_by='TicketType.created_at',
    )
    gatemen = relationship(
        'Gateman', back_populates='event', cascade='all, delete-orphan',
    )

    __table_args__ = (
        Index('ix_events_status_start', 'status', 'start_at'),
        Index('ix_events_promoter', 'promoter_id'),
        Index('ix_events_mode', 'mode'),
    )

    @property
    def is_past(self):
        if not self.end_at:
            return False
        return self.end_at < datetime.now(timezone.utc)

    @property
    def color_pair(self):
        """Returns a (primary, secondary) tuple of hex strings, or defaults."""
        if self.color_scheme:
            parts = [p.strip() for p in self.color_scheme.split(',') if p.strip()]
            if len(parts) >= 2:
                return parts[0], parts[1]
        return '#c026d3', '#facc15'  # magenta, electric yellow

    def to_dict(self, *, include_ticket_types=False, viewer=None):
        d = {
            'id': str(self.id),
            'promoter_id': str(self.promoter_id),
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'start_at': self.start_at.isoformat() if self.start_at else None,
            'end_at': self.end_at.isoformat() if self.end_at else None,
            'location': self.location,
            'poster_url': self.poster_url,
            'poster_thumb_url': self.poster_thumb_url,
            'color_scheme': self.color_scheme,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'mode': self.mode,
            'external_link': self.external_link,
            'whatsapp_deep_link_text': self.whatsapp_deep_link_text,
            'is_past': self.is_past,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        # Denormalise promoter light info for cards.
        if self.promoter:
            d['promoter'] = {
                'id': str(self.promoter.id),
                'name': self.promoter.name,
                'phone': self.promoter.phone,
            }
            profile = getattr(self.promoter, 'promoter_profile', None)
            if profile:
                d['promoter']['organisation_name'] = profile.organisation_name
                d['promoter']['bio'] = profile.bio
                d['promoter']['photo_url'] = profile.photo_url
        if include_ticket_types:
            # Only emit ticket types for ticketed mode. For flyer events, empty list.
            if self.mode == 'ticketed':
                d['ticket_types'] = [t.to_dict() for t in self.ticket_types]
            else:
                d['ticket_types'] = []
        return d


# ---------------------------------------------------------------------------
# TicketType — the Listing in PurchaseInterface terms.
# ---------------------------------------------------------------------------
class TicketType(db.Model):
    __tablename__ = 'ticket_types'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'),
                      nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    price_usd = Column(Numeric(10, 2), nullable=False, default=0)
    quantity_total = Column(Integer, nullable=False, default=0)
    quantity_sold = Column(Integer, nullable=False, default=0)
    quantity_held = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False,
                        default=utcnow, onupdate=utcnow)

    event = relationship('Event', back_populates='ticket_types')

    __table_args__ = (
        CheckConstraint('quantity_total >= 0', name='ck_tt_total_nonneg'),
        CheckConstraint('quantity_sold >= 0', name='ck_tt_sold_nonneg'),
        CheckConstraint('quantity_held >= 0', name='ck_tt_held_nonneg'),
        CheckConstraint('price_usd >= 0', name='ck_tt_price_nonneg'),
    )

    @property
    def quantity_remaining(self):
        return int(self.quantity_total or 0) - int(self.quantity_sold or 0) - int(self.quantity_held or 0)

    def to_dict(self):
        return {
            'id': str(self.id),
            'event_id': str(self.event_id),
            'name': self.name,
            'description': self.description,
            'price_usd': str(self.price_usd) if self.price_usd is not None else None,
            'quantity_total': self.quantity_total,
            'quantity_sold': self.quantity_sold,
            'quantity_held': self.quantity_held,
            'quantity_remaining': self.quantity_remaining,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Ticket — the delivered good.
# ---------------------------------------------------------------------------
class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_type_id = Column(UUID(as_uuid=True), ForeignKey('ticket_types.id'),
                            nullable=False, index=True)

    # Nullable for comp / walk-in direct mints; FK enforced when set.
    purchase_id = Column(UUID(as_uuid=True), ForeignKey('purchases.id'),
                         nullable=True, index=True)

    attendee_name = Column(String(80), nullable=False)
    source = Column(String(20), nullable=False, default='online')

    # Walk-in buyer overrides (the buyer is not a host user in that case).
    walk_in_name = Column(String(120), nullable=True)
    walk_in_phone = Column(String(20), nullable=True)
    walk_in_email = Column(String(255), nullable=True)

    price_usd = Column(Numeric(10, 2), nullable=False, default=0)
    payment_ref = Column(String(120), nullable=True)

    # The full HMAC-signed payload string: <uuid>.<random>.<sig>
    qr_code = Column(String(200), nullable=False, unique=True)

    # NOTE: the explicit Index('ix_tickets_status') in __table_args__ below is
    # the single source of truth for this index. We deliberately do NOT also
    # set index=True here — that would auto-generate a second index with the
    # same name and break db.create_all() (used by `manage.py reset`).
    status = Column(String(20), nullable=False, default='valid')
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey('gatemen.id'),
                           nullable=True)
    checked_in_device = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    ticket_type = relationship('TicketType')
    purchase = relationship('Purchase', foreign_keys=[purchase_id])
    gateman = relationship('Gateman', foreign_keys=[checked_in_by])

    __table_args__ = (
        Index('ix_tickets_purchase', 'purchase_id'),
        Index('ix_tickets_status', 'status'),
        CheckConstraint('price_usd >= 0', name='ck_tickets_price_nonneg'),
    )

    def buyer_view(self):
        """Compact buyer-facing record (no admin/internal data)."""
        tt = self.ticket_type
        ev = tt.event if tt else None
        d = {
            'id': str(self.id),
            'attendee_name': self.attendee_name,
            'status': self.status,
            'source': self.source,
            'price_usd': str(self.price_usd) if self.price_usd is not None else None,
            'qr_code': self.qr_code,
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if tt:
            d['ticket_type'] = {
                'id': str(tt.id),
                'name': tt.name,
                'price_usd': str(tt.price_usd),
            }
        if ev:
            d['event'] = {
                'id': str(ev.id),
                'title': ev.title,
                'start_at': ev.start_at.isoformat() if ev.start_at else None,
                'end_at': ev.end_at.isoformat() if ev.end_at else None,
                'location': ev.location,
                'poster_thumb_url': ev.poster_thumb_url or ev.poster_url,
                'category': ev.category,
            }
        return d

    def attendees_row(self):
        """Promoter-facing per-ticket row for the attendees list / CSV."""
        # Buyer identity: online → linked Purchase; walk-in → walk_in_* cols; comp → none.
        buyer_name = buyer_phone = buyer_email = None
        if self.source == 'online' and self.purchase and self.purchase.buyer:
            buyer_name = self.purchase.buyer.name
            buyer_phone = self.purchase.buyer.phone
            buyer_email = self.purchase.buyer.email
        elif self.source == 'walk_in':
            buyer_name = self.walk_in_name
            buyer_phone = self.walk_in_phone
            buyer_email = self.walk_in_email

        # Display-stripped payment ref (snip > 30 chars for screen).
        pref = self.payment_ref or ''
        if pref and len(pref) > 30:
            pref_display = pref[:24] + '…'
        else:
            pref_display = pref or None

        gateman_name = self.gateman.name if self.gateman else None

        return {
            'id': str(self.id),
            'short_id': str(self.id)[:8].upper(),
            'attendee_name': self.attendee_name,
            'source': self.source,
            'ticket_type': self.ticket_type.name if self.ticket_type else None,
            'ticket_type_id': str(self.ticket_type_id),
            'price_usd': str(self.price_usd),
            'payment_ref_display': pref_display,
            'payment_ref_full': pref,
            'status': self.status,
            'checked_in': self.status == 'used',
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None,
            'gateman_name': gateman_name,
            'buyer_name': buyer_name,
            'buyer_phone': buyer_phone,
            'buyer_email': buyer_email,
            'purchase_id': str(self.purchase_id) if self.purchase_id else None,
            'purchase_status': self.purchase.status if self.purchase else None,
        }


# ---------------------------------------------------------------------------
# Gateman — per-event door scanner credential.
# ---------------------------------------------------------------------------
class Gateman(db.Model):
    __tablename__ = 'gatemen'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'),
                      nullable=False, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    pin_hash = Column(String(255), nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'),
                        nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    scan_count = Column(Integer, nullable=False, default=0)

    event = relationship('Event', back_populates='gatemen')

    __table_args__ = (
        # phones unique per event (a phone can be reused for different events).
        UniqueConstraint('event_id', 'phone', name='uq_gatemen_event_phone'),
    )

    def to_dict(self, *, include_pin_meta=False):
        d = {
            'id': str(self.id),
            'event_id': str(self.event_id),
            'name': self.name,
            'phone': self.phone,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'scan_count': self.scan_count,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        return d

    @property
    def is_active(self):
        from datetime import datetime, timezone
        if self.revoked_at is not None:
            return False
        if self.locked_until is not None and self.locked_until < datetime.now(timezone.utc):
            return False
        return True


# ---------------------------------------------------------------------------
# Checkin — immutable audit row.
# ---------------------------------------------------------------------------
class Checkin(db.Model):
    __tablename__ = 'checkins'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id'),
                      nullable=False, index=True)
    gateman_id = Column(UUID(as_uuid=True), ForeignKey('gatemen.id'),
                       nullable=False)
    scanned_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    synced_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    device_id = Column(String(100), nullable=True)
    result = Column(String(20), nullable=False)


__all__ = [
    'Event', 'TicketType', 'Ticket', 'Gateman', 'Checkin',
    'EVENT_STATUSES', 'EVENT_CATEGORIES', 'EVENT_MODES',
    'TICKET_STATUSES', 'TICKET_SOURCES', 'CHECKIN_RESULTS',
]
