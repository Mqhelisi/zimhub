"""ProviderService — the service catalog. Per STAGE_4_SPEC.md §5.2.1.

Each row is its own BookingInterface bookable ("the bookable is the SERVICE,
not the provider"); the provider's calendar gates conflict detection across
all of their services uniformly.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, ForeignKey,
    CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


PRICING_UNITS = ('flat', 'per_hour', 'per_day', 'per_km')
TRADES = (
    'Plumber', 'Electrician', 'Hairdresser', 'Driver', 'Maid', 'Mechanic',
    'Tutor', 'Photographer-for-hire', 'Other',
)


class ProviderService(db.Model):
    __tablename__ = 'provider_services'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'),
                              nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    pricing_unit = Column(String(20), nullable=False)   # flat | per_hour | per_day | per_km
    rate_usd = Column(Numeric(10, 2), nullable=False)
    default_duration_minutes = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default='active')   # active | archived
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow,
                        onupdate=utcnow)

    provider = relationship('User')

    __table_args__ = (
        CheckConstraint("pricing_unit IN ('flat','per_hour','per_day','per_km')",
                        name='ck_provider_services_pricing_unit'),
        CheckConstraint('rate_usd >= 0', name='ck_provider_services_rate_nonneg'),
        Index('ix_provider_services_provider_status', 'provider_user_id', 'status'),
    )

    def to_dict(self):
        return {
            'id': str(self.id),
            'provider_user_id': str(self.provider_user_id),
            'name': self.name,
            'description': self.description,
            'pricing_unit': self.pricing_unit,
            'rate_usd': str(self.rate_usd),
            'default_duration_minutes': self.default_duration_minutes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
