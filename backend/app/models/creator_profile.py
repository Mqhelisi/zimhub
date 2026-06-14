"""CreatorProfile — per spec §4.3."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class CreatorProfile(db.Model):
    __tablename__ = 'creator_profiles'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    display_name = Column(String(200), nullable=False)
    creator_slug = Column(String(200), unique=True, nullable=False, index=True)
    creator_types = Column(ARRAY(String), nullable=False, default=list)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    discipline_tags = Column(ARRAY(String), nullable=False, default=list)
    social_links = Column(JSONB, nullable=False, default=dict)
    external_links = Column(JSONB, nullable=False, default=dict)
    accent_color = Column(String(7), nullable=True)
    hero_image_url = Column(String(500), nullable=True)
    # Stage 5 / CreatorPlatform §5.1 — page module ordering + featured items.
    # Shape: {"order": ["music","gallery","events"], "featured_track_id": "..."}
    module_order = Column(JSONB, nullable=False, default=dict)
    contact_email = Column(String(255), nullable=True)
    contact_email_public = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default='approved')
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship('User', back_populates='creator_profile')

    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'display_name': self.display_name,
            'creator_slug': self.creator_slug,
            'creator_types': list(self.creator_types or []),
            'bio': self.bio,
            'photo_url': self.photo_url,
            'discipline_tags': list(self.discipline_tags or []),
            'social_links': self.social_links or {},
            'external_links': self.external_links or {},
            'accent_color': self.accent_color,
            'hero_image_url': self.hero_image_url,
            'module_order': self.module_order or {},
            'contact_email': self.contact_email,
            'contact_email_public': self.contact_email_public,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
