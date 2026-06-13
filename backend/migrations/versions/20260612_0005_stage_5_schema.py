"""stage 5 schema — CreatorPlatform tables + creator_profiles.module_order

Revision ID: 20260612_0005
Revises: 20260610_0004
Create Date: 2026-06-12 00:00:00

Additive only — no changes to any Stage 1–4 table beyond one new column on the
existing creator_profiles shell.

Adds:
  - creator_profiles.module_order        (JSONB; page module order / featured)
  - creator_tracks                       (Musician content + play_count)
  - creator_play_events                  (per-play log, session-deduped)
  - creator_gallery_collections          (Photographer / Visual Artist sets)
  - creator_gallery_items                (gallery images)
  - creator_events                       (dual-mode: host_ticketing → TG, or external)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260612_0005'
down_revision = '20260610_0004'
branch_labels = None
depends_on = None


def upgrade():
    # ---- additive column on the Stage 1 creator_profiles shell ----
    op.add_column(
        'creator_profiles',
        sa.Column('module_order', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # ---------------- creator_tracks ----------------
    op.create_table(
        'creator_tracks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_profiles.user_id'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('featuring', sa.String(length=200), nullable=True),
        sa.Column('album', sa.String(length=200), nullable=True),
        sa.Column('genre', sa.String(length=80), nullable=True),
        sa.Column('cover_art_url', sa.String(length=500), nullable=True),
        sa.Column('audio_url', sa.String(length=500), nullable=False),
        sa.Column('cloudinary_public_id', sa.String(length=200), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('moderation_note', sa.Text(), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_creator_tracks_creator_id', 'creator_tracks', ['creator_id'])
    op.create_index('ix_creator_tracks_creator_visible', 'creator_tracks',
                    ['creator_id', 'is_visible'])

    # ---------------- creator_play_events ----------------
    op.create_table(
        'creator_play_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('track_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_tracks.id'), nullable=False),
        sa.Column('session_id', sa.String(length=120), nullable=True),
        sa.Column('played_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_creator_play_events_track_id', 'creator_play_events', ['track_id'])
    op.create_index('ix_creator_play_events_track_session', 'creator_play_events',
                    ['track_id', 'session_id'])

    # ---------------- creator_gallery_collections ----------------
    op.create_table(
        'creator_gallery_collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_profiles.user_id'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_creator_gallery_collections_creator_id',
                    'creator_gallery_collections', ['creator_id'])

    # ---------------- creator_gallery_items ----------------
    op.create_table(
        'creator_gallery_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_profiles.user_id'), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_gallery_collections.id'), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=40), nullable=True),
        sa.Column('year_created', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=False),
        sa.Column('cloudinary_public_id', sa.String(length=200), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_creator_gallery_items_creator_id',
                    'creator_gallery_items', ['creator_id'])
    op.create_index('ix_creator_gallery_items_collection_id',
                    'creator_gallery_items', ['collection_id'])

    # ---------------- creator_events ----------------
    op.create_table(
        'creator_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('creator_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('creator_profiles.user_id'), nullable=False),
        sa.Column('submitted_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('venue_name', sa.String(length=300), nullable=True),
        sa.Column('google_maps_url', sa.String(length=500), nullable=True),
        sa.Column('poster_url', sa.String(length=500), nullable=True),
        sa.Column('ticketing_mode', sa.String(length=20), nullable=False),
        sa.Column('host_event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id'), nullable=True),
        sa.Column('ticket_price', sa.String(length=40), nullable=True),
        sa.Column('external_ticket_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='approved'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_creator_events_creator_id', 'creator_events', ['creator_id'])
    op.create_index('ix_creator_events_host_event_id', 'creator_events', ['host_event_id'])


def downgrade():
    op.drop_table('creator_events')
    op.drop_table('creator_gallery_items')
    op.drop_table('creator_gallery_collections')
    op.drop_table('creator_play_events')
    op.drop_table('creator_tracks')
    op.drop_column('creator_profiles', 'module_order')
