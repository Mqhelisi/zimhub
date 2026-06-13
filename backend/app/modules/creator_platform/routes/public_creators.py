"""Public CreatorPlatform routes — CreatorPlatform_Spec.md §10 (public surface).

No auth required (anonymous streaming/browsing preserved). Mounted under /api.

  GET  /api/creators                      discovery (filter ?type= &q=)
  GET  /api/creators/types                type registry
  GET  /api/creators/search?q=&type=      grouped search
  GET  /api/creators/landing              module landing (top tracks / new / featured)
  GET  /api/creators/:slug                full type-aware page payload
  GET  /api/creators/:slug/tracks         visible tracks
  GET  /api/creators/:slug/gallery        visible collections + items
  GET  /api/creators/:slug/events         approved events
  POST /api/creators/tracks/:id/play      record a play (30s rule, session-deduped)
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from extensions import db
from app.models import CreatorProfile
from app.utils.errors import not_found, validation_failed

from ..models import Track, GalleryCollection, GalleryItem, CreatorEvent, PlayEvent
from ..types import registry_payload
from ..serializers import (
    public_creator_payload, discovery_list, creator_card,
)

log = logging.getLogger('zimhub.creator_platform.public')

public_creators_bp = Blueprint('creator_platform_public', __name__,
                               url_prefix='/api/creators')


def _load_profile_by_slug(slug):
    return (CreatorProfile.query
            .filter(CreatorProfile.creator_slug == slug,
                    CreatorProfile.status == 'approved')
            .first())


# ---------------------------------------------------------------------------
# Type registry — static route BEFORE the <slug> catch-all.
# ---------------------------------------------------------------------------
@public_creators_bp.get('/types')
def list_types():
    return jsonify({'types': registry_payload()})


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
@public_creators_bp.get('')
@public_creators_bp.get('/')
def list_creators():
    type_filter = (request.args.get('type') or '').strip().lower() or None
    q = (request.args.get('q') or '').strip() or None
    return jsonify({'creators': discovery_list(type_filter=type_filter, q=q)})


# ---------------------------------------------------------------------------
# Module landing — featured / top tracks / new releases / upcoming events
# ---------------------------------------------------------------------------
@public_creators_bp.get('/landing')
def landing():
    now = datetime.now(timezone.utc)
    top_tracks = (Track.query.filter(Track.is_visible.is_(True))
                  .order_by(Track.play_count.desc(), Track.uploaded_at.desc())
                  .limit(10).all())
    new_tracks = (Track.query.filter(Track.is_visible.is_(True))
                  .order_by(Track.uploaded_at.desc()).limit(6).all())
    featured_gallery = (GalleryItem.query.filter(GalleryItem.is_visible.is_(True))
                        .order_by(GalleryItem.uploaded_at.desc()).limit(6).all())
    creators = discovery_list()
    upcoming = (CreatorEvent.query
                .filter(CreatorEvent.status == 'approved',
                        CreatorEvent.event_date >= now)
                .order_by(CreatorEvent.event_date.asc()).limit(4).all())
    return jsonify({
        'featured_creators': creators[:6],
        'top_tracks': [t.to_dict(include_creator=True) for t in top_tracks],
        'new_releases': [t.to_dict(include_creator=True) for t in new_tracks],
        'featured_gallery': [g.to_dict() for g in featured_gallery],
        'upcoming_events': [e.to_dict(include_host_event=True) for e in upcoming],
    })


# ---------------------------------------------------------------------------
# Search — grouped by entity (tracks / creators / gallery / events)
# ---------------------------------------------------------------------------
@public_creators_bp.get('/search')
def search():
    q = (request.args.get('q') or '').strip()
    type_scope = (request.args.get('type') or 'all').strip().lower()
    if not q:
        return jsonify({'query': q, 'tracks': [], 'creators': [],
                        'gallery': [], 'events': []})
    like = f'%{q.lower()}%'
    out = {'query': q, 'tracks': [], 'creators': [], 'gallery': [], 'events': []}

    if type_scope in ('all', 'tracks'):
        rows = (Track.query.filter(Track.is_visible.is_(True),
                                   db.func.lower(Track.title).like(like))
                .limit(20).all())
        out['tracks'] = [t.to_dict(include_creator=True) for t in rows]
    if type_scope in ('all', 'creators'):
        out['creators'] = discovery_list(q=q)
    if type_scope in ('all', 'gallery'):
        rows = (GalleryItem.query.filter(
                    GalleryItem.is_visible.is_(True),
                    db.or_(db.func.lower(GalleryItem.title).like(like),
                           db.func.lower(GalleryItem.category).like(like)))
                .limit(20).all())
        out['gallery'] = [g.to_dict() for g in rows]
    if type_scope in ('all', 'events'):
        rows = (CreatorEvent.query.filter(
                    CreatorEvent.status == 'approved',
                    db.func.lower(CreatorEvent.title).like(like))
                .limit(20).all())
        out['events'] = [e.to_dict() for e in rows]
    return jsonify(out)


# ---------------------------------------------------------------------------
# Creator page payload (type-aware) + sub-resources
# ---------------------------------------------------------------------------
@public_creators_bp.get('/<slug>')
def get_creator(slug):
    profile = _load_profile_by_slug(slug)
    if not profile:
        return not_found('Creator not found.')
    return jsonify({'creator': public_creator_payload(profile)})


@public_creators_bp.get('/<slug>/tracks')
def get_creator_tracks(slug):
    profile = _load_profile_by_slug(slug)
    if not profile:
        return not_found('Creator not found.')
    rows = (Track.query.filter(Track.creator_id == profile.user_id,
                               Track.is_visible.is_(True))
            .order_by(Track.position.asc(), Track.uploaded_at.desc()).all())
    return jsonify({'tracks': [t.to_dict() for t in rows]})


@public_creators_bp.get('/<slug>/gallery')
def get_creator_gallery(slug):
    profile = _load_profile_by_slug(slug)
    if not profile:
        return not_found('Creator not found.')
    cols = (GalleryCollection.query
            .filter(GalleryCollection.creator_id == profile.user_id)
            .order_by(GalleryCollection.created_at.asc()).all())
    return jsonify({'collections': [c.to_dict(include_items=True) for c in cols]})


@public_creators_bp.get('/<slug>/events')
def get_creator_events(slug):
    profile = _load_profile_by_slug(slug)
    if not profile:
        return not_found('Creator not found.')
    rows = (CreatorEvent.query
            .filter(CreatorEvent.creator_id == profile.user_id,
                    CreatorEvent.status == 'approved')
            .order_by(CreatorEvent.event_date.asc()).all())
    return jsonify({'events': [e.to_dict(include_host_event=True) for e in rows]})


# ---------------------------------------------------------------------------
# Record a play — counted once per session per track (CreatorPlatform §5.2/§14)
# ---------------------------------------------------------------------------
@public_creators_bp.post('/tracks/<track_id>/play')
def record_play(track_id):
    track = db.session.get(Track, track_id)
    if not track or not track.is_visible:
        return not_found('Track not found.')
    data = request.get_json(silent=True) or {}
    session_id = (data.get('session_id') or '').strip() or None

    # Dedupe: one count per (track, session). Anonymous (no session) always counts.
    already = False
    if session_id:
        already = (PlayEvent.query
                   .filter(PlayEvent.track_id == track.id,
                           PlayEvent.session_id == session_id)
                   .first() is not None)
    if not already:
        db.session.add(PlayEvent(track_id=track.id, session_id=session_id))
        track.play_count = (track.play_count or 0) + 1
        db.session.commit()
    return jsonify({'ok': True, 'play_count': track.play_count})
