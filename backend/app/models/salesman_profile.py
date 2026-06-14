"""SalesmanProfile — per spec §4.3.

Per-product/inventory tables are deferred to Stage 2 (PurchaseInterface ships them).
This shell holds the shop identity + slug.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SalesmanProfile(db.Model):
    __tablename__ = 'salesman_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    shop_name = Column(String(200), nullable=False)
    shop_slug = Column(String(200), unique=True, nullable=False, index=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    pickup_delivery_policy = Column(Text, nullable=True)
    default_currency = Column(String(3), nullable=False, default='USD')
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship('User', back_populates='salesman_profile')

    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'shop_name': self.shop_name,
            'shop_slug': self.shop_slug,
            'bio': self.bio,
            'photo_url': self.photo_url,
            'banner_url': self.banner_url,
            'pickup_delivery_policy': self.pickup_delivery_policy,
            'default_currency': self.default_currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
