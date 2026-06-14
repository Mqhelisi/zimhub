"""Notification model — per spec §4.4.

`kind` is intentionally an open string (not an enum) — Stage 2+ will add more
kinds (purchase_initiated, payment_confirmed, etc.) without DB migrations.
"""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    kind = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)  # column name 'metadata' is reserved by SQLAlchemy
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = relationship('User', back_populates='notifications')

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'kind': self.kind,
            'title': self.title,
            'body': self.body,
            'metadata': self.metadata_json or {},
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
