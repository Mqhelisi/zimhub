"""PurchaseInterface data model — per PURCHASE_INTERFACE_SPEC.md §6.

Tables:
    purchases           — the transaction record itself
    purchase_events     — immutable transition log
    disputes            — escalations + admin resolutions

All IDs UUID v4, all timestamps timezone-aware UTC, money numeric(10, 2) USD.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# State machine states — per spec §4.
PURCHASE_STATUSES = (
    'awaiting_payment',
    'awaiting_buyer_confirmation',
    'completed',
    'cancelled',
    'expired',
    'disputed',
    'refunded',
)


class Purchase(db.Model):
    """One transaction: a buyer acquiring a quantity of one Listing from its seller.

    The Listing is polymorphic — `(listing_type, listing_id)` is the foreign
    reference into the domain module's listing table. The handler registered
    for `listing_type` knows how to resolve, decrement, and fulfill it.
    """
    __tablename__ = 'purchases'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    listing_type = Column(String(50), nullable=False)
    listing_id = Column(UUID(as_uuid=True), nullable=False)

    seller_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    quantity = Column(Integer, nullable=False)
    unit_price_usd = Column(Numeric(10, 2), nullable=False)  # snapshot at initiation
    total_usd = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')

    status = Column(String(40), nullable=False, default='awaiting_payment', index=True)
    payment_ref = Column(String(120), nullable=True)  # seller-entered, e.g. Ecocash code

    domain_payload = Column(JSONB, nullable=True)         # opaque blob from buyer client
    fulfillment_refs = Column(JSONB, nullable=True)       # returned by on_payment_confirmed

    hold_expires_at = Column(DateTime(timezone=True), nullable=True)
    auto_complete_at = Column(DateTime(timezone=True), nullable=True)
    seller_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    buyer_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    dispute_id = Column(UUID(as_uuid=True), ForeignKey('disputes.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    seller = relationship('User', foreign_keys=[seller_id])
    buyer = relationship('User', foreign_keys=[buyer_id])
    events = relationship(
        'PurchaseEvent',
        back_populates='purchase',
        cascade='all, delete-orphan',
        order_by='PurchaseEvent.created_at',
    )
    disputes = relationship(
        'PurchaseDispute',
        back_populates='purchase',
        foreign_keys='PurchaseDispute.purchase_id',
        order_by='PurchaseDispute.created_at',
    )

    __table_args__ = (
        Index('ix_purchases_seller_status_created', 'seller_id', 'status', 'created_at'),
        Index('ix_purchases_buyer_status_created', 'buyer_id', 'status', 'created_at'),
        Index('ix_purchases_status_hold_expires', 'status', 'hold_expires_at'),
        Index('ix_purchases_status_auto_complete', 'status', 'auto_complete_at'),
        Index('ix_purchases_listing', 'listing_type', 'listing_id'),
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def is_terminal(self) -> bool:
        return self.status in ('completed', 'cancelled', 'expired', 'refunded')

    @property
    def is_active(self) -> bool:
        """True while the Purchase is still in a working state (not terminal)."""
        return self.status in ('awaiting_payment', 'awaiting_buyer_confirmation', 'disputed')

    def has_open_dispute(self) -> bool:
        for d in self.disputes:
            if d.status == 'open':
                return True
        return False

    # ------------------------------------------------------------------
    # Permitted actions — what the *current viewer* may do right now.
    # Used by the frontend to decide which buttons to render.
    # ------------------------------------------------------------------
    def permitted_actions_for(self, user) -> list:
        if not user:
            return []
        actions = []
        is_buyer = str(user.id) == str(self.buyer_id)
        is_seller = str(user.id) == str(self.seller_id)
        is_admin = bool(getattr(user, 'is_super_admin', False))

        if self.status == 'awaiting_payment':
            if is_seller:
                actions += ['confirm_payment', 'cancel']
            if is_buyer:
                actions += ['cancel', 'dispute']
            actions.append('whatsapp')
        elif self.status == 'awaiting_buyer_confirmation':
            if is_buyer:
                actions += ['confirm_receipt', 'dispute']
            actions.append('whatsapp')
        elif self.status == 'disputed':
            if is_admin:
                actions.append('resolve_dispute')

        return actions

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self, viewer=None, include_events=False):
        d = {
            'id': str(self.id),
            'listing_type': self.listing_type,
            'listing_id': str(self.listing_id),
            'seller_id': str(self.seller_id),
            'buyer_id': str(self.buyer_id),
            'quantity': self.quantity,
            'unit_price_usd': str(self.unit_price_usd) if self.unit_price_usd is not None else None,
            'total_usd': str(self.total_usd) if self.total_usd is not None else None,
            'currency': self.currency,
            'status': self.status,
            'payment_ref': self.payment_ref,
            'domain_payload': self.domain_payload or None,
            'fulfillment_refs': self.fulfillment_refs or None,
            'hold_expires_at': self.hold_expires_at.isoformat() if self.hold_expires_at else None,
            'auto_complete_at': self.auto_complete_at.isoformat() if self.auto_complete_at else None,
            'seller_confirmed_at': self.seller_confirmed_at.isoformat() if self.seller_confirmed_at else None,
            'buyer_confirmed_at': self.buyer_confirmed_at.isoformat() if self.buyer_confirmed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'has_open_dispute': self.has_open_dispute(),
        }
        # Denormalise counterparty light info so frontend doesn't need extra fetches.
        if self.seller:
            d['seller'] = {
                'id': str(self.seller.id),
                'name': self.seller.name,
                'phone': self.seller.phone,
                'email': self.seller.email,
            }
            if getattr(self.seller, 'salesman_profile', None):
                p = self.seller.salesman_profile
                d['seller']['shop_name'] = p.shop_name
                d['seller']['shop_slug'] = p.shop_slug
        if self.buyer:
            d['buyer'] = {
                'id': str(self.buyer.id),
                'name': self.buyer.name,
                'phone': self.buyer.phone,
                'email': self.buyer.email,
            }
        if viewer is not None:
            d['permitted_actions'] = self.permitted_actions_for(viewer)
        if include_events:
            d['events'] = [e.to_dict() for e in self.events]
            d['dispute'] = None
            for disp in self.disputes:
                if disp.status == 'open':
                    d['dispute'] = disp.to_dict()
                    break
            if d['dispute'] is None and self.disputes:
                d['dispute'] = self.disputes[-1].to_dict()
        return d


class PurchaseEvent(db.Model):
    """Immutable transition log. One row per state change."""
    __tablename__ = 'purchase_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    purchase_id = Column(UUID(as_uuid=True), ForeignKey('purchases.id'), nullable=False, index=True)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_role = Column(String(20), nullable=False)  # buyer | seller | admin | system
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    purchase = relationship('Purchase', back_populates='events')

    def to_dict(self):
        return {
            'id': str(self.id),
            'purchase_id': str(self.purchase_id),
            'from_status': self.from_status,
            'to_status': self.to_status,
            'actor_id': str(self.actor_id) if self.actor_id else None,
            'actor_role': self.actor_role,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PurchaseDispute(db.Model):
    """A dispute raised by buyer or seller; resolved by admin."""
    __tablename__ = 'disputes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # NOTE: cross-table FK back to purchases is also created from Purchase.dispute_id.
    # We don't constraint here to avoid cycles; the integrity check is logical.
    purchase_id = Column(UUID(as_uuid=True), ForeignKey('purchases.id'), nullable=False, index=True)
    raised_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    raised_by_role = Column(String(20), nullable=False)  # buyer | seller
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default='open')  # open | resolved
    resolution = Column(String(20), nullable=True)  # completed | refunded | cancelled
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    purchase = relationship('Purchase', back_populates='disputes', foreign_keys=[purchase_id])
    raiser = relationship('User', foreign_keys=[raised_by])
    resolver = relationship('User', foreign_keys=[resolved_by])

    __table_args__ = (
        Index('ix_disputes_status_created', 'status', 'created_at'),
    )

    def to_dict(self, include_purchase=False):
        d = {
            'id': str(self.id),
            'purchase_id': str(self.purchase_id),
            'raised_by': str(self.raised_by),
            'raised_by_role': self.raised_by_role,
            'reason': self.reason,
            'status': self.status,
            'resolution': self.resolution,
            'resolution_note': self.resolution_note,
            'resolved_by': str(self.resolved_by) if self.resolved_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if self.raiser:
            d['raiser_name'] = self.raiser.name
        if include_purchase and self.purchase:
            d['purchase'] = self.purchase.to_dict(include_events=True)
        return d
