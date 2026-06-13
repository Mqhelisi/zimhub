"""CreatorPlatform models — per CreatorPlatform_Spec.md §9 + Stage 5 §5.1.

Tables owned here (all prefixed to coexist with host tables):
    creator_tracks            — Musician content (audio + cover art)
    creator_play_events       — per-play log (30s-rule, session-deduped)
    creator_gallery_collections — Photographer / Visual Artist collections
    creator_gallery_items     — gallery images
    creator_events            — dual-mode events (ticketed via TG, or free/external)

NOT owned here:
    creator_profiles / users  — host tables (Stage 1). `creator_id` below is the
        creator's user_id (creator_profiles PK == user_id), so a creator's
        content keys directly to their host identity. This is what lets the
        event bridge set TicketGenerator `Event.promoter_id = creator_id`.
    events / ticket_types / tickets — TicketGenerator (Stage 3). A ticketed
        creator event's `host_event_id` points at a real TG `events.id`.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# Status / enum sets (validated at route layer; stored as strings for portability)
GALLERY_CATEGORIES = (
    'photography', 'painting', 'sculpture', 'fabricated', 'digital',
)
CREATOR_EVENT_MODES = ('host_ticketing', 'external')
CREATOR_EVENT_STATUSES = ('pending', 'approved', 'rejected')


# ---------------------------------------------------------------------------
# Track — Musician content
# ---------------------------------------------------------------------------
class Track(db.Model):
    __tablename__ = 'creator_tracks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(UUID(as_uuid=True),
                        ForeignKey('creator_profiles.user_id'),
                        nullable=False, index=True)
    title = Column(String(200), nullable=False)
    featuring = Column(String(200), nullable=True)
    album = Column(String(200), nullable=True)
    genre = Column(String(80), nullable=True)
    cover_art_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=False)
    cloudinary_public_id = Column(String(200), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    is_visible = Column(Boolean, nullable=False, default=True)
    moderation_note = Column(Text, nullable=True)
    play_count = Column(Integer, nullable=False, default=0)
    position = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    creator = relationship('CreatorProfile', foreign_keys=[creator_id])

    __table_args__ = (
        Index('ix_creator_tracks_creator_visible', 'creator_id', 'is_visible'),
    )

    def to_dict(self, *, include_creator=False):
        d = {
            'id': str(self.id),
            'creator_id': str(self.creator_id),
            'title': self.title,
            'featuring': self.featuring,
            'album': self.album,
            'genre': self.genre,
            'cover_art_url': self.cover_art_url,
            'audio_url': self.audio_url,
            'duration_seconds': self.duration_seconds,
            'is_visible': self.is_visible,
            'play_count': self.play_count,
            'position': self.position,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
        if include_creator and self.creator:
            d['creator'] = {
                'user_id': str(self.creator.user_id),
                'display_name': self.creator.display_name,
                'creator_slug': self.creator.creator_slug,
                'accent_color': self.creator.accent_color,
            }
        return d


# ---------------------------------------------------------------------------
# PlayEvent — per-play audit (play counted after 30s, deduped per session/track)
# ---------------------------------------------------------------------------
class PlayEvent(db.Model):
    __tablename__ = 'creator_play_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey('creator_tracks.id'),
                      nullable=False, index=True)
    session_id = Column(String(120), nullable=True)
    played_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index('ix_creator_play_events_track_session', 'track_id', 'session_id'),
    )


# ---------------------------------------------------------------------------
# GalleryCollection — Photographer / Visual Artist
# ---------------------------------------------------------------------------
class GalleryCollection(db.Model):
    __tablename__ = 'creator_gallery_collections'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(UUID(as_uuid=True),
                        ForeignKey('creator_profiles.user_id'),
                        nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    creator = relationship('CreatorProfile', foreign_keys=[creator_id])
    items = relationship('GalleryItem', back_populates='collection',
                         cascade='all, delete-orphan',
                         order_by='GalleryItem.uploaded_at')

    def to_dict(self, *, include_items=False):
        d = {
            'id': str(self.id),
            'creator_id': str(self.creator_id),
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'item_count': len([i for i in self.items if i.is_visible]) if self.items is not None else 0,
        }
        if include_items:
            d['items'] = [i.to_dict() for i in self.items if i.is_visible]
        return d


# ---------------------------------------------------------------------------
# GalleryItem — a single image
# ---------------------------------------------------------------------------
class GalleryItem(db.Model):
    __tablename__ = 'creator_gallery_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(UUID(as_uuid=True),
                        ForeignKey('creator_profiles.user_id'),
                        nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True),
                           ForeignKey('creator_gallery_collections.id'),
                           nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(40), nullable=True)
    year_created = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=False)
    cloudinary_public_id = Column(String(200), nullable=True)
    is_visible = Column(Boolean, nullable=False, default=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    creator = relationship('CreatorProfile', foreign_keys=[creator_id])
    collection = relationship('GalleryCollection', back_populates='items')

    def to_dict(self):
        return {
            'id': str(self.id),
            'creator_id': str(self.creator_id),
            'collection_id': str(self.collection_id) if self.collection_id else None,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'year_created': self.year_created,
            'image_url': self.image_url,
            'is_visible': self.is_visible,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ---------------------------------------------------------------------------
# CreatorEvent — dual-mode (host_ticketing via TG, or external/free)
# ---------------------------------------------------------------------------
class CreatorEvent(db.Model):
    __tablename__ = 'creator_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    creator_id = Column(UUID(as_uuid=True),
                        ForeignKey('creator_profiles.user_id'),
                        nullable=False, index=True)
    submitted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'),
                          nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=False)
    venue_name = Column(String(300), nullable=True)
    google_maps_url = Column(String(500), nullable=True)
    poster_url = Column(String(500), nullable=True)

    ticketing_mode = Column(String(20), nullable=False)   # host_ticketing | external

    # Mode A (host_ticketing): the linked real TicketGenerator event.
    host_event_id = Column(UUID(as_uuid=True), ForeignKey('events.id'),
                           nullable=True, index=True)
    # Mode B (external): free or off-platform.
    ticket_price = Column(String(40), nullable=True)        # 'free' or price string
    external_ticket_url = Column(String(500), nullable=True)

    # Post-moderation by default (auto-approved at create) — Stage 5 §11/§5.2:
    # the host consolidates onboarding gating; per-event approval is relaxed so
    # an approved creator can publish and sell immediately (acceptance 87/93).
    status = Column(String(20), nullable=False, default='approved')
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    creator = relationship('CreatorProfile', foreign_keys=[creator_id])
    host_event = relationship('Event', foreign_keys=[host_event_id])

    def to_dict(self, *, include_host_event=False):
        d = {
            'id': str(self.id),
            'creator_id': str(self.creator_id),
            'submitted_by': str(self.submitted_by),
            'title': self.title,
            'description': self.description,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'venue_name': self.venue_name,
            'google_maps_url': self.google_maps_url,
            'poster_url': self.poster_url,
            'ticketing_mode': self.ticketing_mode,
            'host_event_id': str(self.host_event_id) if self.host_event_id else None,
            'ticket_price': self.ticket_price,
            'external_ticket_url': self.external_ticket_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if self.creator:
            d['creator'] = {
                'user_id': str(self.creator.user_id),
                'display_name': self.creator.display_name,
                'creator_slug': self.creator.creator_slug,
                'accent_color': self.creator.accent_color,
            }
        if include_host_event and self.host_event is not None:
            d['host_event'] = self.host_event.to_dict(include_ticket_types=True)
        return d


__all__ = [
    'Track', 'PlayEvent', 'GalleryCollection', 'GalleryItem', 'CreatorEvent',
    'GALLERY_CATEGORIES', 'CREATOR_EVENT_MODES', 'CREATOR_EVENT_STATUSES',
]
