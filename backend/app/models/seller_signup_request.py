"""SellerSignupRequest — per spec §4.2.

category_payload shape per category (validated in routes/schemas):
- salesman: {shop_name, primary_category, sample_products, pickup_delivery_preference}
- promoter: {organisation_name?, past_events?, sample_poster_url?, event_categories[]}
- provider: {trade, years_experience, service_areas[], pricing_unit_preference}
- creator:  {creator_types[], sample_work_urls[], discipline_tags[]}
"""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class SellerSignupRequest(db.Model):
    __tablename__ = 'seller_signup_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category = Column(String(20), nullable=False)
    full_name = Column(String(200), nullable=False)
    business_name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    suburb = Column(String(100), nullable=False)
    pitch = Column(Text, nullable=False)  # ≤500 chars (validated)
    category_payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default='pending')  # pending | approved | rejected
    rejection_reason = Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'category': self.category,
            'full_name': self.full_name,
            'business_name': self.business_name,
            'email': self.email,
            'phone': self.phone,
            'suburb': self.suburb,
            'pitch': self.pitch,
            'category_payload': self.category_payload or {},
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'reviewed_by': str(self.reviewed_by) if self.reviewed_by else None,
            'created_user_id': str(self.created_user_id) if self.created_user_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
