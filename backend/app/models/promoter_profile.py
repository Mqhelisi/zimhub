"""PromoterProfile — per spec §4.3."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class PromoterProfile(db.Model):
    __tablename__ = 'promoter_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    organisation_name = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    default_currency = Column(String(3), nullable=False, default='USD')
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship('User', back_populates='promoter_profile')

    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'organisation_name': self.organisation_name,
            'bio': self.bio,
            'photo_url': self.photo_url,
            'default_currency': self.default_currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
