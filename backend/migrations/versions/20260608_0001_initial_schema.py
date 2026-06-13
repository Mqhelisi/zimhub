"""initial schema — Stage 1

Revision ID: 20260608_0001
Revises:
Create Date: 2026-06-08 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260608_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ---------------- users ----------------
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('suburb', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False, server_default='Bulawayo'),
        sa.Column('is_buyer', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_salesman', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_promoter', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_provider', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_creator', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_super_admin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_phone', 'users', ['phone'])
    op.create_index('ix_users_is_salesman_true', 'users', ['is_salesman'],
                    postgresql_where=sa.text('is_salesman = true'))
    op.create_index('ix_users_is_promoter_true', 'users', ['is_promoter'],
                    postgresql_where=sa.text('is_promoter = true'))
    op.create_index('ix_users_is_provider_true', 'users', ['is_provider'],
                    postgresql_where=sa.text('is_provider = true'))
    op.create_index('ix_users_is_creator_true', 'users', ['is_creator'],
                    postgresql_where=sa.text('is_creator = true'))
    op.create_index('ix_users_is_super_admin_true', 'users', ['is_super_admin'],
                    postgresql_where=sa.text('is_super_admin = true'))

    # ---------------- password_reset_tokens ----------------
    op.create_table(
        'password_reset_tokens',
        sa.Column('token', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])

    # ---------------- seller_signup_requests ----------------
    op.create_table(
        'seller_signup_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('business_name', sa.String(length=200), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('suburb', sa.String(length=100), nullable=False),
        sa.Column('pitch', sa.Text(), nullable=False),
        sa.Column('category_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ssr_status_created', 'seller_signup_requests', ['status', sa.text('created_at desc')])
    op.create_index('ix_ssr_category_status', 'seller_signup_requests', ['category', 'status'])

    # ---------------- salesman_profiles ----------------
    op.create_table(
        'salesman_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('shop_name', sa.String(length=200), nullable=False),
        sa.Column('shop_slug', sa.String(length=200), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('banner_url', sa.String(length=500), nullable=True),
        sa.Column('pickup_delivery_policy', sa.Text(), nullable=True),
        sa.Column('default_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('shop_slug', name='uq_salesman_profiles_shop_slug'),
    )
    op.create_index('ix_salesman_profiles_shop_slug', 'salesman_profiles', ['shop_slug'], unique=True)

    # ---------------- promoter_profiles ----------------
    op.create_table(
        'promoter_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('organisation_name', sa.String(length=200), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('default_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- provider_profiles ----------------
    op.create_table(
        'provider_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('trade', sa.String(length=100), nullable=False),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('suburbs_served', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('default_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Africa/Harare'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ---------------- creator_profiles ----------------
    op.create_table(
        'creator_profiles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('creator_slug', sa.String(length=200), nullable=False),
        sa.Column('creator_types', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('discipline_tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('social_links', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('external_links', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('accent_color', sa.String(length=7), nullable=True),
        sa.Column('hero_image_url', sa.String(length=500), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_email_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='approved'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('creator_slug', name='uq_creator_profiles_creator_slug'),
    )
    op.create_index('ix_creator_profiles_creator_slug', 'creator_profiles', ['creator_slug'], unique=True)

    # ---------------- notifications ----------------
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

    # ---------------- mock_messages ----------------
    op.create_table(
        'mock_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_mock_messages_created_at', 'mock_messages', ['created_at'])


def downgrade():
    op.drop_index('ix_mock_messages_created_at', table_name='mock_messages')
    op.drop_table('mock_messages')

    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')

    op.drop_index('ix_creator_profiles_creator_slug', table_name='creator_profiles')
    op.drop_table('creator_profiles')

    op.drop_table('provider_profiles')
    op.drop_table('promoter_profiles')

    op.drop_index('ix_salesman_profiles_shop_slug', table_name='salesman_profiles')
    op.drop_table('salesman_profiles')

    op.drop_index('ix_ssr_category_status', table_name='seller_signup_requests')
    op.drop_index('ix_ssr_status_created', table_name='seller_signup_requests')
    op.drop_table('seller_signup_requests')

    op.drop_index('ix_password_reset_tokens_user_id', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')

    for ix in (
        'ix_users_is_super_admin_true',
        'ix_users_is_creator_true',
        'ix_users_is_provider_true',
        'ix_users_is_promoter_true',
        'ix_users_is_salesman_true',
        'ix_users_phone',
        'ix_users_email',
    ):
        op.drop_index(ix, table_name='users')
    op.drop_table('users')
