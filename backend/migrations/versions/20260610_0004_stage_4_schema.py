"""stage 4 schema — BookingInterface + Services section tables

Revision ID: 20260610_0004
Revises: 20260609_0003
Create Date: 2026-06-10 00:00:00

Adds:
  - bi_provider_profiles    (BI spec §7 `provider_profiles`; prefixed — the
                             host already owns a provider_profiles table)
  - availability_rules
  - availability_blocks
  - booking_disputes        (BI spec §7 `disputes`; prefixed — Purchase-
                             Interface already owns a disputes table)
  - bookings
  - booking_events
  - provider_services       (Stage 4 spec §5.2.1)

No changes to any Stage 1–3 table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260610_0004'
down_revision = '20260609_0003'
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- bi_provider_profiles ----------------
    op.create_table(
        'bi_provider_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('slug', sa.String(length=220), nullable=False, unique=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('timezone', sa.Text(), nullable=False,
                  server_default='Africa/Harare'),
        sa.Column('hourly_rate_usd', sa.Numeric(10, 2), nullable=True),
        sa.Column('min_hours', sa.Integer(), nullable=True),
        sa.Column('max_hours', sa.Integer(), nullable=True),
        sa.Column('response_hours', sa.Integer(), nullable=True),
        sa.Column('cancel_cutoff_hours', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_bi_provider_profiles_slug', 'bi_provider_profiles', ['slug'])

    # ---------------- availability_rules ----------------
    op.create_table(
        'availability_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.CheckConstraint('weekday >= 0 AND weekday <= 6',
                           name='ck_availability_rules_weekday'),
        sa.CheckConstraint('start_time < end_time',
                           name='ck_availability_rules_order'),
    )
    op.create_index('ix_availability_rules_provider_weekday',
                    'availability_rules', ['provider_id', 'weekday'])

    # ---------------- availability_blocks ----------------
    op.create_table(
        'availability_blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.CheckConstraint('start_at < end_at',
                           name='ck_availability_blocks_order'),
    )
    op.create_index('ix_availability_blocks_provider_start',
                    'availability_blocks', ['provider_id', 'start_at'])

    # ---------------- booking_disputes (created before bookings: FK) -------
    op.create_table(
        'booking_disputes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raised_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('raised_by_role', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='open'),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_booking_disputes_booking_id', 'booking_disputes',
                    ['booking_id'])

    # ---------------- bookings ----------------
    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bookable_type', sa.String(length=50), nullable=False,
                  server_default='service_provider'),
        sa.Column('bookable_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_hours', sa.Numeric(5, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='requested'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('quoted_rate_usd', sa.Numeric(10, 2), nullable=True),
        sa.Column('domain_payload', postgresql.JSONB(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider_responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('no_show', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cancelled_by', sa.String(length=20), nullable=True),
        sa.Column('cancel_reason', sa.Text(), nullable=True),
        sa.Column('dispute_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('booking_disputes.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('start_at < end_at', name='ck_bookings_range_order'),
    )
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    op.create_index('ix_bookings_provider_status_start', 'bookings',
                    ['provider_id', 'status', 'start_at'])
    op.create_index('ix_bookings_requester_status_start', 'bookings',
                    ['requester_id', 'status', 'start_at'])
    op.create_index('ix_bookings_status_expires', 'bookings',
                    ['status', 'expires_at'])
    op.create_index('ix_bookings_status_end', 'bookings', ['status', 'end_at'])
    op.create_index('ix_bookings_bookable', 'bookings',
                    ['bookable_type', 'bookable_id'])

    op.create_foreign_key('fk_booking_disputes_booking_id', 'booking_disputes',
                          'bookings', ['booking_id'], ['id'])

    # ---------------- booking_events ----------------
    op.create_table(
        'booking_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=True),
        sa.Column('to_status', sa.String(length=20), nullable=False),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(length=20), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_booking_events_booking_id', 'booking_events',
                    ['booking_id'])

    # ---------------- provider_services ----------------
    op.create_table(
        'provider_services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider_user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('pricing_unit', sa.String(length=20), nullable=False),
        sa.Column('rate_usd', sa.Numeric(10, 2), nullable=False),
        sa.Column('default_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "pricing_unit IN ('flat','per_hour','per_day','per_km')",
            name='ck_provider_services_pricing_unit'),
        sa.CheckConstraint('rate_usd >= 0',
                           name='ck_provider_services_rate_nonneg'),
    )
    op.create_index('ix_provider_services_provider_user_id',
                    'provider_services', ['provider_user_id'])
    op.create_index('ix_provider_services_provider_status',
                    'provider_services', ['provider_user_id', 'status'])


def downgrade():
    op.drop_table('provider_services')
    op.drop_table('booking_events')
    op.drop_constraint('fk_booking_disputes_booking_id', 'booking_disputes',
                       type_='foreignkey')
    op.drop_table('bookings')
    op.drop_table('booking_disputes')
    op.drop_table('availability_blocks')
    op.drop_table('availability_rules')
    op.drop_table('bi_provider_profiles')
