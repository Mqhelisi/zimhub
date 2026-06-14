"""ProviderProfile — per spec §4.3."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ProviderProfile(db.Model):
    __tablename__ = 'provider_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    trade = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    suburbs_served = Column(ARRAY(String), nullable=False, default=list)
    default_currency = Column(String(3), nullable=False, default='USD')
    timezone = Column(String(50), nullable=False, default='Africa/Harare')
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship('User', back_populates='provider_profile')

    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'trade': self.trade,
            'bio': self.bio,
            'photo_url': self.photo_url,
            'suburbs_served': list(self.suburbs_served or []),
            'default_currency': self.default_currency,
            'timezone': self.timezone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
