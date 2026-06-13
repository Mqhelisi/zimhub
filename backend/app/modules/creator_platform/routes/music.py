"""Music management routes — CreatorPlatform_Spec.md §5.2 / §6. Auth + is_creator.

  GET    /api/creator/tracks            own tracks (all, incl. hidden)
  POST   /api/creator/tracks            create a track (audio_url from /uploads/audio)
  PATCH  /api/creator/tracks/:id        edit metadata / visibility
  DELETE /api/creator/tracks/:id        delete own track
  POST   /api/creator/tracks/reorder    set track positions
"""
import logging

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import forbidden, validation_failed, not_found

from ..models import Track, PlayEvent

log = logging.getLogger('zimhub.creator_platform.music')

music_bp = Blueprint('creator_platform_music', __name__,
                     url_prefix='/api/creator')


def _require_creator(user):
    if not user.is_creator:
        return None, forbidden('You need a Creator capability to access this.')
    if user.creator_profile is None:
        return None, forbidden('Your creator profile is not provisioned yet.')
    return user.creator_profile, None


def _load_own_track(profile, track_id):
    t = db.session.get(Track, track_id)
    if not t:
        return None, not_found('Track not found.')
    if str(t.creator_id) != str(profile.user_id):
        return None, forbidden('Not your track.')
    return t, None


@music_bp.get('/tracks')
@require_auth
def list_tracks(user):
    profile, err = _require_creator(user)
    if err:
        return err
    rows = (Track.query.filter(Track.creator_id == profile.user_id)
            .order_by(Track.position.asc(), Track.uploaded_at.desc()).all())
    return jsonify({'tracks': [t.to_dict() for t in rows]})


@music_bp.post('/tracks')
@require_auth
def create_track(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    field_errors = {}
    title = (data.get('title') or '').strip()
    audio_url = (data.get('audio_url') or '').strip()
    if not title:
        field_errors['title'] = 'Required.'
    if not audio_url:
        field_errors['audio_url'] = 'Upload an audio file first.'
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    max_pos = db.session.query(db.func.coalesce(db.func.max(Track.position), -1)) \
        .filter(Track.creator_id == profile.user_id).scalar()
    t = Track(
        creator_id=profile.user_id,
        title=title[:200],
        featuring=(data.get('featuring') or '').strip() or None,
        album=(data.get('album') or '').strip() or None,
        genre=(data.get('genre') or '').strip() or None,
        cover_art_url=(data.get('cover_art_url') or '').strip() or None,
        audio_url=audio_url,
        cloudinary_public_id=(data.get('cloudinary_public_id') or '').strip() or None,
        duration_seconds=data.get('duration_seconds') if isinstance(data.get('duration_seconds'), int) else None,
        position=(max_pos or -1) + 1,
        is_visible=True,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({'track': t.to_dict()}), 201


@music_bp.patch('/tracks/<track_id>')
@require_auth
def edit_track(user, track_id):
    profile, err = _require_creator(user)
    if err:
        return err
    t, terr = _load_own_track(profile, track_id)
    if terr:
        return terr
    data = request.get_json(silent=True) or {}
    if 'title' in data:
        v = (data.get('title') or '').strip()
        if v:
            t.title = v[:200]
    for f in ('featuring', 'album', 'genre', 'cover_art_url'):
        if f in data:
            setattr(t, f, (data.get(f) or '').strip() or None)
    if 'is_visible' in data:
        t.is_visible = bool(data['is_visible'])
    db.session.commit()
    return jsonify({'track': t.to_dict()})


@music_bp.delete('/tracks/<track_id>')
@require_auth
def delete_track(user, track_id):
    profile, err = _require_creator(user)
    if err:
        return err
    t, terr = _load_own_track(profile, track_id)
    if terr:
        return terr
    PlayEvent.query.filter(PlayEvent.track_id == t.id).delete()
    db.session.delete(t)
    db.session.commit()
    return jsonify({'ok': True})


@music_bp.post('/tracks/reorder')
@require_auth
def reorder_tracks(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    order = data.get('track_ids') or []
    if not isinstance(order, list):
        return validation_failed('track_ids must be a list.')
    pos = 0
    for tid in order:
        t = db.session.get(Track, tid)
        if t and str(t.creator_id) == str(profile.user_id):
            t.position = pos
            pos += 1
    db.session.commit()
    rows = (Track.query.filter(Track.creator_id == profile.user_id)
            .order_by(Track.position.asc()).all())
    return jsonify({'tracks': [t.to_dict() for t in rows]})
