"""stage 2 schema — products + PurchaseInterface tables

Revision ID: 20260608_0002
Revises: 20260608_0001
Create Date: 2026-06-08 00:00:00

Adds:
  - products
  - purchases
  - purchase_events
  - disputes
And the cross-FK from purchases.dispute_id -> disputes.id.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260608_0002'
down_revision = '20260608_0001'
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- products ----------------
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('salesman_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('price_usd', sa.Numeric(10, 2), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stock_held', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stock_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('photos', postgresql.ARRAY(sa.String()), nullable=False,
                  server_default=sa.text("ARRAY[]::varchar[]")),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint('stock_quantity >= 0', name='ck_products_stock_quantity_nonneg'),
        sa.CheckConstraint('stock_held >= 0', name='ck_products_stock_held_nonneg'),
        sa.CheckConstraint('stock_sold >= 0', name='ck_products_stock_sold_nonneg'),
        sa.CheckConstraint('price_usd >= 0', name='ck_products_price_nonneg'),
    )
    op.create_index('ix_products_salesman_user_id', 'products', ['salesman_user_id'])
    op.create_index('ix_products_category', 'products', ['category'])
    op.create_index('ix_products_salesman_status', 'products', ['salesman_user_id', 'status'])
    op.create_index('ix_products_category_status', 'products', ['category', 'status'])

    # ---------------- disputes ----------------
    # Created before purchases to keep the FK simple; purchases.dispute_id is
    # added with a separate constraint after both tables exist.
    op.create_table(
        'disputes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('purchase_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raised_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('raised_by_role', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_disputes_purchase_id', 'disputes', ['purchase_id'])
    op.create_index('ix_disputes_created_at', 'disputes', ['created_at'])
    op.create_index('ix_disputes_status_created', 'disputes', ['status', 'created_at'])

    # ---------------- purchases ----------------
    op.create_table(
        'purchases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('listing_type', sa.String(length=50), nullable=False),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seller_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('buyer_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price_usd', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_usd', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='awaiting_payment'),
        sa.Column('payment_ref', sa.String(length=120), nullable=True),
        sa.Column('domain_payload', postgresql.JSONB(), nullable=True),
        sa.Column('fulfillment_refs', postgresql.JSONB(), nullable=True),
        sa.Column('hold_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_complete_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('seller_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('buyer_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dispute_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('disputes.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_purchases_status', 'purchases', ['status'])
    op.create_index('ix_purchases_seller_status_created', 'purchases',
                    ['seller_id', 'status', 'created_at'])
    op.create_index('ix_purchases_buyer_status_created', 'purchases',
                    ['buyer_id', 'status', 'created_at'])
    op.create_index('ix_purchases_status_hold_expires', 'purchases',
                    ['status', 'hold_expires_at'])
    op.create_index('ix_purchases_status_auto_complete', 'purchases',
                    ['status', 'auto_complete_at'])
    op.create_index('ix_purchases_listing', 'purchases', ['listing_type', 'listing_id'])

    # Add the cross-FK from disputes.purchase_id back to purchases.id now that
    # purchases exists.
    op.create_foreign_key(
        'fk_disputes_purchase_id_purchases',
        'disputes', 'purchases',
        ['purchase_id'], ['id'],
    )

    # ---------------- purchase_events ----------------
    op.create_table(
        'purchase_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('purchase_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('purchases.id'), nullable=False),
        sa.Column('from_status', sa.String(length=40), nullable=True),
        sa.Column('to_status', sa.String(length=40), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(length=20), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_purchase_events_purchase_id', 'purchase_events', ['purchase_id'])


def downgrade():
    op.drop_index('ix_purchase_events_purchase_id', table_name='purchase_events')
    op.drop_table('purchase_events')

    op.drop_constraint('fk_disputes_purchase_id_purchases', 'disputes', type_='foreignkey')

    op.drop_index('ix_purchases_listing', table_name='purchases')
    op.drop_index('ix_purchases_status_auto_complete', table_name='purchases')
    op.drop_index('ix_purchases_status_hold_expires', table_name='purchases')
    op.drop_index('ix_purchases_buyer_status_created', table_name='purchases')
    op.drop_index('ix_purchases_seller_status_created', table_name='purchases')
    op.drop_index('ix_purchases_status', table_name='purchases')
    op.drop_table('purchases')

    op.drop_index('ix_disputes_status_created', table_name='disputes')
    op.drop_index('ix_disputes_created_at', table_name='disputes')
    op.drop_index('ix_disputes_purchase_id', table_name='disputes')
    op.drop_table('disputes')

    op.drop_index('ix_products_category_status', table_name='products')
    op.drop_index('ix_products_salesman_status', table_name='products')
    op.drop_index('ix_products_category', table_name='products')
    op.drop_index('ix_products_salesman_user_id', table_name='products')
    op.drop_table('products')
