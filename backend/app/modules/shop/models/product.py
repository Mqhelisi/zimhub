"""Product model — per STAGE_2_SPEC.md §5.2.1.

Stock semantics:
    available = stock_quantity - stock_held - stock_sold
    stock_held increments on on_initiate, decrements on cancel/expire/confirm.
    stock_sold increments on payment confirmed.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, DateTime, ForeignKey,
    CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Product(db.Model):
    __tablename__ = 'products'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    salesman_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price_usd = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    stock_held = Column(Integer, nullable=False, default=0)
    stock_sold = Column(Integer, nullable=False, default=0)
    photos = Column(ARRAY(String), nullable=False, default=list)
    status = Column(String(20), nullable=False, default='active')  # active | draft | archived
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    salesman = relationship('User')

    __table_args__ = (
        CheckConstraint('stock_quantity >= 0', name='ck_products_stock_quantity_nonneg'),
        CheckConstraint('stock_held >= 0', name='ck_products_stock_held_nonneg'),
        CheckConstraint('stock_sold >= 0', name='ck_products_stock_sold_nonneg'),
        CheckConstraint('price_usd >= 0', name='ck_products_price_nonneg'),
        Index('ix_products_salesman_status', 'salesman_user_id', 'status'),
        Index('ix_products_category_status', 'category', 'status'),
    )

    @property
    def available(self) -> int:
        return int(self.stock_quantity or 0) - int(self.stock_held or 0) - int(self.stock_sold or 0)

    def to_dict(self, with_salesman=False):
        d = {
            'id': str(self.id),
            'salesman_user_id': str(self.salesman_user_id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price_usd': str(self.price_usd) if self.price_usd is not None else None,
            'stock_quantity': self.stock_quantity,
            'stock_held': self.stock_held,
            'stock_sold': self.stock_sold,
            'available': self.available,
            'photos': list(self.photos or []),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if with_salesman and self.salesman is not None:
            profile = getattr(self.salesman, 'salesman_profile', None)
            d['salesman'] = {
                'user_id': str(self.salesman.id),
                'name': self.salesman.name,
                'phone': self.salesman.phone,
                'shop_name': profile.shop_name if profile else self.salesman.name,
                'shop_slug': profile.shop_slug if profile else None,
                'photo_url': profile.photo_url if profile else None,
            }
        return d
