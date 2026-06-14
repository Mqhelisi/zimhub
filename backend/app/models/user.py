"""User + password reset token models. Per spec §4.1.

PasswordResetToken is included here (not its own file) because it's tightly
coupled to User and only used by the auth flow.
"""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(200), nullable=False)
    suburb = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False, default='Bulawayo')

    is_buyer = Column(Boolean, nullable=False, default=True)
    is_salesman = Column(Boolean, nullable=False, default=False)
    is_promoter = Column(Boolean, nullable=False, default=False)
    is_provider = Column(Boolean, nullable=False, default=False)
    is_creator = Column(Boolean, nullable=False, default=False)
    is_super_admin = Column(Boolean, nullable=False, default=False)

    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_required = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default='active')  # active | suspended

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    notifications = relationship(
        'Notification', back_populates='user', cascade='all, delete-orphan'
    )
    salesman_profile = relationship(
        'SalesmanProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )
    promoter_profile = relationship(
        'PromoterProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )
    provider_profile = relationship(
        'ProviderProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )
    creator_profile = relationship(
        'CreatorProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )

    def capabilities_dict(self):
        return {
            'is_buyer': self.is_buyer,
            'is_salesman': self.is_salesman,
            'is_promoter': self.is_promoter,
            'is_provider': self.is_provider,
            'is_creator': self.is_creator,
            'is_super_admin': self.is_super_admin,
        }

    def to_dict(self, include_capabilities=True):
        d = {
            'id': str(self.id),
            'email': self.email,
            'phone': self.phone,
            'name': self.name,
            'suburb': self.suburb,
            'city': self.city,
            'status': self.status,
            'password_reset_required': self.password_reset_required,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_capabilities:
            d.update(self.capabilities_dict())
        return d


class PasswordResetToken(db.Model):
    """Spec §5.1: separate password_reset_tokens table, single-use, 1h expiry."""
    __tablename__ = 'password_reset_tokens'

    token = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
