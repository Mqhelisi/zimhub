"""BookingInterface data model — per BOOKING_INTERFACE_SPEC.md §7.

Tables:
    bi_provider_profiles  — module-owned provider booking settings
    availability_rules    — recurring weekly open hours
    availability_blocks   — one-off unavailable ranges
    bookings              — the agreement record itself
    booking_events        — immutable transition log
    booking_disputes      — optional escalations (late cancel / no-show)

NAMING NOTES (documented deviations, table names only — column names match
the BI spec verbatim):
  - BI spec calls its provider-settings table `provider_profiles`, but the
    host (Stage 1) already owns a `provider_profiles` table. The module table
    is therefore named `bi_provider_profiles`. All field names match §7.
  - BI spec calls its dispute table `disputes`, but PurchaseInterface (Stage 2)
    already owns `disputes`. The module table is therefore named
    `booking_disputes`. The two dispute systems are deliberately independent.

All IDs UUID v4, timestamps timezone-aware UTC, money numeric(10,2) USD —
informational only; BookingInterface never moves money.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, Boolean, DateTime, Time,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# State machine states — per BI spec §4.
BOOKING_STATUSES = (
    'requested',
    'confirmed',
    'declined',
    'cancelled',
    'expired',
    'completed',
    'no_show',
    'disputed',
)

# States that lock the provider's calendar for [start_at, end_at).
CALENDAR_LOCKING_STATUSES = ('confirmed',)


class BIProviderProfile(db.Model):
    """Module-owned provider booking settings (BI spec §7 `provider_profiles`).

    `provider_id` is the host user id. The host's own provider_profiles row
    (trade/bio/photo/suburbs) stays host-owned; this row carries the
    booking-specific settings the BI spec defines, plus the public slug the
    Services section uses for provider URLs.
    """
    __tablename__ = 'bi_provider_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(
        UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True,
    )
    display_name = Column(Text, nullable=False)
    slug = Column(String(220), nullable=False, unique=True, index=True)
    bio = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False, default='Africa/Harare')
    hourly_rate_usd = Column(Numeric(10, 2), nullable=True)  # display only, unverified
    min_hours = Column(Integer, nullable=True)
    max_hours = Column(Integer, nullable=True)
    response_hours = Column(Integer, nullable=True)   # tightens expires_at if set
    cancel_cutoff_hours = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    provider = relationship('User')

    def to_dict(self):
        return {
            'id': str(self.id),
            'provider_id': str(self.provider_id),
            'display_name': self.display_name,
            'slug': self.slug,
            'bio': self.bio,
            'timezone': self.timezone,
            'hourly_rate_usd': str(self.hourly_rate_usd) if self.hourly_rate_usd is not None else None,
            'min_hours': self.min_hours,
            'max_hours': self.max_hours,
            'response_hours': self.response_hours,
            'cancel_cutoff_hours': self.cancel_cutoff_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AvailabilityRule(db.Model):
    """Recurring weekly open hours — BI spec §7. Times local to provider tz."""
    __tablename__ = 'availability_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    weekday = Column(Integer, nullable=False)   # 0=Mon … 6=Sun
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    __table_args__ = (
        CheckConstraint('weekday >= 0 AND weekday <= 6', name='ck_availability_rules_weekday'),
        CheckConstraint('start_time < end_time', name='ck_availability_rules_order'),
        Index('ix_availability_rules_provider_weekday', 'provider_id', 'weekday'),
    )

    def to_dict(self):
        return {
            'id': str(self.id),
            'provider_id': str(self.provider_id),
            'weekday': self.weekday,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
        }


class AvailabilityBlock(db.Model):
    """One-off unavailable range — BI spec §7."""
    __tablename__ = 'availability_blocks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint('start_at < end_at', name='ck_availability_blocks_order'),
        Index('ix_availability_blocks_provider_start', 'provider_id', 'start_at'),
    )

    def to_dict(self):
        return {
            'id': str(self.id),
            'provider_id': str(self.provider_id),
            'start_at': self.start_at.isoformat(),
            'end_at': self.end_at.isoformat(),
            'reason': self.reason,
        }


class Booking(db.Model):
    """One request for a time range [start_at, end_at) against a provider.

    Per BI spec §7. `bookable_type`/`bookable_id` are polymorphic into the
    domain handler's table (Stage 4: provider_services rows).
    """
    __tablename__ = 'bookings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    bookable_type = Column(String(50), nullable=False, default='service_provider')
    bookable_id = Column(UUID(as_uuid=True), nullable=False)

    provider_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    requester_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    duration_hours = Column(Numeric(5, 2), nullable=False)

    status = Column(String(20), nullable=False, default='requested', index=True)
    message = Column(Text, nullable=True)
    quoted_rate_usd = Column(Numeric(10, 2), nullable=True)  # informational snapshot

    domain_payload = Column(JSONB, nullable=True)  # opaque blob from the domain module

    expires_at = Column(DateTime(timezone=True), nullable=True)
    provider_responded_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    no_show = Column(Boolean, nullable=False, default=False)
    cancelled_by = Column(String(20), nullable=True)   # requester | provider | admin
    cancel_reason = Column(Text, nullable=True)
    dispute_id = Column(UUID(as_uuid=True), ForeignKey('booking_disputes.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    provider = relationship('User', foreign_keys=[provider_id])
    requester = relationship('User', foreign_keys=[requester_id])
    events = relationship(
        'BookingEvent', back_populates='booking',
        cascade='all, delete-orphan', order_by='BookingEvent.created_at',
    )
    disputes = relationship(
        'BookingDispute', back_populates='booking',
        foreign_keys='BookingDispute.booking_id', order_by='BookingDispute.created_at',
    )

    __table_args__ = (
        CheckConstraint('start_at < end_at', name='ck_bookings_range_order'),
        Index('ix_bookings_provider_status_start', 'provider_id', 'status', 'start_at'),
        Index('ix_bookings_requester_status_start', 'requester_id', 'status', 'start_at'),
        Index('ix_bookings_status_expires', 'status', 'expires_at'),
        Index('ix_bookings_status_end', 'status', 'end_at'),
        Index('ix_bookings_bookable', 'bookable_type', 'bookable_id'),
    )

    # ------------------------------------------------------------------
    @property
    def is_terminal(self) -> bool:
        return self.status in ('declined', 'cancelled', 'expired', 'completed', 'no_show')

    def has_open_dispute(self) -> bool:
        return any(d.status == 'open' for d in self.disputes)

    def permitted_actions(self, viewer, *, now=None) -> list:
        """What the current viewer may do right now — BI spec §8 GET /bookings/:id."""
        from app.services import host  # late import; avoids cycles
        now = now or utcnow()
        actions = []
        if viewer is None:
            return actions
        is_requester = str(viewer.id) == str(self.requester_id)
        is_provider = str(viewer.id) == str(self.provider_id)
        is_admin = bool(getattr(viewer, 'is_super_admin', False))

        cutoff_hours = int(host.config('CANCEL_CUTOFF_HOURS', 0) or 0)
        prof = BIProviderProfile.query.filter_by(provider_id=self.provider_id).first()
        if prof and prof.cancel_cutoff_hours is not None:
            cutoff_hours = prof.cancel_cutoff_hours
        from datetime import timedelta
        cancellable_until = self.start_at - timedelta(hours=cutoff_hours)
        before_cutoff = now < cancellable_until

        if self.status == 'requested':
            if is_provider:
                actions += ['accept', 'decline']
            if (is_requester or is_provider) and before_cutoff:
                actions.append('cancel')
        elif self.status == 'confirmed':
            if (is_requester or is_provider) and now < self.start_at and before_cutoff:
                actions.append('cancel')
            if is_provider and now > self.start_at:
                actions.append('no_show')
            if (is_requester or is_provider) and not self.has_open_dispute():
                actions.append('dispute')
        elif self.status in ('cancelled', 'no_show', 'completed'):
            if (is_requester or is_provider) and not self.has_open_dispute() and self.status != 'completed':
                actions.append('dispute')
        if self.status == 'disputed' and is_admin:
            actions.append('resolve_dispute')
        if is_requester or is_provider:
            actions.append('whatsapp')
        return actions

    def to_dict(self, viewer=None, include_events=False, label=None):
        d = {
            'id': str(self.id),
            'bookable_type': self.bookable_type,
            'bookable_id': str(self.bookable_id),
            'provider_id': str(self.provider_id),
            'requester_id': str(self.requester_id),
            'start_at': self.start_at.isoformat(),
            'end_at': self.end_at.isoformat(),
            'duration_hours': str(self.duration_hours),
            'status': self.status,
            'message': self.message,
            'quoted_rate_usd': str(self.quoted_rate_usd) if self.quoted_rate_usd is not None else None,
            'domain_payload': self.domain_payload or {},
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'provider_responded_at': self.provider_responded_at.isoformat() if self.provider_responded_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'no_show': self.no_show,
            'cancelled_by': self.cancelled_by,
            'cancel_reason': self.cancel_reason,
            'dispute_id': str(self.dispute_id) if self.dispute_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if label:
            d['label'] = label
        if viewer is not None:
            d['permitted_actions'] = self.permitted_actions(viewer)
            d['provider'] = {
                'id': str(self.provider_id),
                'name': self.provider.name if self.provider else None,
                'phone': self.provider.phone if self.provider else None,
            }
            # Requester details are visible to the provider and admin only.
            if str(viewer.id) == str(self.provider_id) or getattr(viewer, 'is_super_admin', False) \
                    or str(viewer.id) == str(self.requester_id):
                d['requester'] = {
                    'id': str(self.requester_id),
                    'name': self.requester.name if self.requester else None,
                    'phone': self.requester.phone if self.requester else None,
                }
        if include_events:
            d['events'] = [e.to_dict() for e in self.events]
            d['disputes'] = [x.to_dict() for x in self.disputes]
        return d


class BookingEvent(db.Model):
    """Immutable transition log — BI spec §7."""
    __tablename__ = 'booking_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.id'), nullable=False, index=True)
    from_status = Column(String(20), nullable=True)
    to_status = Column(String(20), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)   # null for system
    actor_role = Column(String(20), nullable=False)        # requester|provider|admin|system
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    booking = relationship('Booking', back_populates='events')

    def to_dict(self):
        return {
            'id': str(self.id),
            'booking_id': str(self.booking_id),
            'from_status': self.from_status,
            'to_status': self.to_status,
            'actor_id': str(self.actor_id) if self.actor_id else None,
            'actor_role': self.actor_role,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BookingDispute(db.Model):
    """Optional light dispute — BI spec §7 (`disputes`; renamed, see header)."""
    __tablename__ = 'booking_disputes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.id'), nullable=False, index=True)
    raised_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    raised_by_role = Column(String(20), nullable=False)   # requester | provider
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='open')   # open | resolved
    resolution = Column(String(20), nullable=True)   # completed | cancelled
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    booking = relationship('Booking', back_populates='disputes', foreign_keys=[booking_id])
    raiser = relationship('User', foreign_keys=[raised_by])

    def to_dict(self, include_booking=False):
        d = {
            'id': str(self.id),
            'booking_id': str(self.booking_id),
            'raised_by': str(self.raised_by),
            'raised_by_name': self.raiser.name if self.raiser else None,
            'raised_by_role': self.raised_by_role,
            'reason': self.reason,
            'status': self.status,
            'resolution': self.resolution,
            'resolution_note': self.resolution_note,
            'resolved_by': str(self.resolved_by) if self.resolved_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if include_booking and self.booking:
            d['booking'] = self.booking.to_dict()
        return d
