"""stage 3 schema — TicketGenerator tables (events, ticket_types, tickets, gatemen, checkins)

Revision ID: 20260609_0003
Revises: 20260608_0002
Create Date: 2026-06-09 00:00:00

Adds:
  - events            (with the Stage 3 §5.3 flyer-extension columns from the start)
  - ticket_types
  - tickets
  - gatemen
  - checkins
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260609_0003'
down_revision = '20260608_0002'
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- events ----------------
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('promoter_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('category', sa.String(length=40), nullable=False, server_default='Other'),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(length=300), nullable=False, server_default=''),
        sa.Column('poster_url', sa.String(length=500), nullable=True),
        sa.Column('poster_thumb_url', sa.String(length=500), nullable=True),
        sa.Column('color_scheme', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        # Stage 3 §5.3 — flyer extension
        sa.Column('mode', sa.String(length=20), nullable=False, server_default='ticketed'),
        sa.Column('external_link', sa.String(length=500), nullable=True),
        sa.Column('whatsapp_deep_link_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_events_promoter_id', 'events', ['promoter_id'])
    op.create_index('ix_events_status', 'events', ['status'])
    op.create_index('ix_events_status_start', 'events', ['status', 'start_at'])
    op.create_index('ix_events_promoter', 'events', ['promoter_id'])
    op.create_index('ix_events_mode', 'events', ['mode'])

    # ---------------- ticket_types ----------------
    op.create_table(
        'ticket_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_usd', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('quantity_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quantity_sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quantity_held', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint('quantity_total >= 0', name='ck_tt_total_nonneg'),
        sa.CheckConstraint('quantity_sold >= 0', name='ck_tt_sold_nonneg'),
        sa.CheckConstraint('quantity_held >= 0', name='ck_tt_held_nonneg'),
        sa.CheckConstraint('price_usd >= 0', name='ck_tt_price_nonneg'),
    )
    op.create_index('ix_ticket_types_event_id', 'ticket_types', ['event_id'])

    # ---------------- gatemen ----------------
    op.create_table(
        'gatemen',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('pin_hash', sa.String(length=255), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_count', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('event_id', 'phone', name='uq_gatemen_event_phone'),
    )
    op.create_index('ix_gatemen_event_id', 'gatemen', ['event_id'])

    # ---------------- tickets ----------------
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_type_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('ticket_types.id'), nullable=False),
        sa.Column('purchase_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('purchases.id'), nullable=True),
        sa.Column('attendee_name', sa.String(length=80), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='online'),
        sa.Column('walk_in_name', sa.String(length=120), nullable=True),
        sa.Column('walk_in_phone', sa.String(length=20), nullable=True),
        sa.Column('walk_in_email', sa.String(length=255), nullable=True),
        sa.Column('price_usd', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('payment_ref', sa.String(length=120), nullable=True),
        sa.Column('qr_code', sa.String(length=200), nullable=False, unique=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='valid'),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checked_in_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('gatemen.id'), nullable=True),
        sa.Column('checked_in_device', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint('price_usd >= 0', name='ck_tickets_price_nonneg'),
    )
    op.create_index('ix_tickets_ticket_type_id', 'tickets', ['ticket_type_id'])
    op.create_index('ix_tickets_purchase_id', 'tickets', ['purchase_id'])
    op.create_index('ix_tickets_status', 'tickets', ['status'])
    op.create_index('ix_tickets_purchase', 'tickets', ['purchase_id'])

    # ---------------- checkins ----------------
    op.create_table(
        'checkins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('tickets.id'), nullable=False),
        sa.Column('gateman_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('gatemen.id'), nullable=False),
        sa.Column('scanned_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=False),
    )
    op.create_index('ix_checkins_ticket_id', 'checkins', ['ticket_id'])


def downgrade():
    op.drop_index('ix_checkins_ticket_id', table_name='checkins')
    op.drop_table('checkins')

    op.drop_index('ix_tickets_purchase', table_name='tickets')
    op.drop_index('ix_tickets_status', table_name='tickets')
    op.drop_index('ix_tickets_purchase_id', table_name='tickets')
    op.drop_index('ix_tickets_ticket_type_id', table_name='tickets')
    op.drop_table('tickets')

    op.drop_index('ix_gatemen_event_id', table_name='gatemen')
    op.drop_table('gatemen')

    op.drop_index('ix_ticket_types_event_id', table_name='ticket_types')
    op.drop_table('ticket_types')

    op.drop_index('ix_events_mode', table_name='events')
    op.drop_index('ix_events_promoter', table_name='events')
    op.drop_index('ix_events_status_start', table_name='events')
    op.drop_index('ix_events_status', table_name='events')
    op.drop_index('ix_events_promoter_id', table_name='events')
    op.drop_table('events')
