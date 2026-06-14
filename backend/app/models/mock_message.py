"""MockMessage — the swap-friendly transport log. Every `host.send(...)` writes
one of these. Per spec §4.5.
"""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class MockMessage(db.Model):
    __tablename__ = 'mock_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    channel = Column(String(20), nullable=False)  # whatsapp | sms | email
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'channel': self.channel,
            'recipient': self.recipient,
            'subject': self.subject,
            'body': self.body,
            'payload': self.payload or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
