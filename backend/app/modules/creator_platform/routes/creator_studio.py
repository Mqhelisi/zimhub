"""Creator Studio routes — CreatorPlatform_Spec.md §6. Auth + is_creator.

  GET   /api/creator/dashboard          counts + recent activity
  GET   /api/creator/profile            own profile (editable form)
  PUT   /api/creator/profile            update profile/page (accent, hero, links, order)
  POST  /api/creator/uploads/image      multipart image (cover/hero/gallery/profile)
  POST  /api/creator/uploads/audio      multipart audio (track)
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from extensions import db
from app.models import CreatorProfile
from app.utils.decorators import require_auth
from app.utils.errors import forbidden, validation_failed, error_response, not_found

from ..models import Track, GalleryCollection, GalleryItem, CreatorEvent
from ..types import CREATOR_TYPES
from ..uploads import upload_image_file, upload_audio_file, UploadError

log = logging.getLogger('zimhub.creator_platform.studio')

creator_studio_bp = Blueprint('creator_platform_studio', __name__,
                              url_prefix='/api/creator')


def _require_creator(user):
    if not user.is_creator:
        return None, forbidden('You need a Creator capability to access this.')
    profile = user.creator_profile
    if profile is None:
        return None, forbidden('Your creator profile is not provisioned yet.')
    return profile, None


_HEX = set('0123456789abcdefABCDEF')


def _valid_hex(c):
    return (isinstance(c, str) and len(c) == 7 and c[0] == '#'
            and all(ch in _HEX for ch in c[1:]))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@creator_studio_bp.get('/dashboard')
@require_auth
def dashboard(user):
    profile, err = _require_creator(user)
    if err:
        return err
    now = datetime.now(timezone.utc)
    track_count = Track.query.filter(Track.creator_id == profile.user_id).count()
    visible_tracks = Track.query.filter(Track.creator_id == profile.user_id,
                                        Track.is_visible.is_(True)).count()
    collection_count = GalleryCollection.query.filter(
        GalleryCollection.creator_id == profile.user_id).count()
    gallery_count = GalleryItem.query.filter(
        GalleryItem.creator_id == profile.user_id).count()
    total_plays = db.session.query(db.func.coalesce(db.func.sum(Track.play_count), 0)) \
        .filter(Track.creator_id == profile.user_id).scalar() or 0
    upcoming_events = (CreatorEvent.query
                       .filter(CreatorEvent.creator_id == profile.user_id,
                               CreatorEvent.event_date >= now)
                       .order_by(CreatorEvent.event_date.asc()).all())
    return jsonify({
        'profile': profile.to_dict(),
        'counts': {
            'tracks': track_count,
            'visible_tracks': visible_tracks,
            'collections': collection_count,
            'gallery_items': gallery_count,
            'total_plays': int(total_plays),
            'upcoming_events': len(upcoming_events),
        },
        'upcoming_events': [e.to_dict(include_host_event=True) for e in upcoming_events],
    })


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@creator_studio_bp.get('/profile')
@require_auth
def get_profile(user):
    profile, err = _require_creator(user)
    if err:
        return err
    return jsonify({'profile': profile.to_dict()})


@creator_studio_bp.put('/profile')
@require_auth
def update_profile(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    field_errors = {}

    if 'display_name' in data:
        v = (data.get('display_name') or '').strip()
        if not v:
            field_errors['display_name'] = 'Required.'
        else:
            profile.display_name = v[:200]
    if 'bio' in data:
        bio = (data.get('bio') or '').strip()
        if len(bio) > 1000:
            field_errors['bio'] = 'Bio must be 1000 characters or fewer.'
        else:
            profile.bio = bio or None
    if 'accent_color' in data:
        c = (data.get('accent_color') or '').strip()
        if c and not _valid_hex(c):
            field_errors['accent_color'] = 'Must be a hex colour like #7c3aed.'
        elif c:
            profile.accent_color = c
    if 'hero_image_url' in data:
        profile.hero_image_url = (data.get('hero_image_url') or '').strip() or None
    if 'photo_url' in data:
        profile.photo_url = (data.get('photo_url') or '').strip() or None
    if 'discipline_tags' in data:
        tags = data.get('discipline_tags') or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        profile.discipline_tags = [str(t)[:40] for t in tags][:12]
    if 'creator_types' in data:
        types = data.get('creator_types') or []
        if isinstance(types, str):
            types = [types]
        clean = [t for t in types if t in CREATOR_TYPES]
        if clean:
            profile.creator_types = clean
        else:
            field_errors['creator_types'] = 'At least one valid type is required.'
    if 'social_links' in data and isinstance(data['social_links'], dict):
        profile.social_links = data['social_links']
    if 'external_links' in data and isinstance(data['external_links'], dict):
        profile.external_links = data['external_links']
    if 'contact_email' in data:
        profile.contact_email = (data.get('contact_email') or '').strip() or None
    if 'contact_email_public' in data:
        profile.contact_email_public = bool(data['contact_email_public'])
    if 'module_order' in data and isinstance(data['module_order'], dict):
        profile.module_order = data['module_order']

    # creator_slug is read-only after first set (§11.10) — never updated here.

    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)
    db.session.commit()
    return jsonify({'profile': profile.to_dict()})


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------
@creator_studio_bp.post('/uploads/image')
@require_auth
def upload_image(user):
    _, err = _require_creator(user)
    if err:
        return err
    fs = request.files.get('file')
    if not fs:
        return validation_failed('file is required (multipart upload).')
    try:
        url = upload_image_file(fs)
    except UploadError as e:
        return error_response(e.code, e.message, e.status)
    except Exception:
        log.exception('Image upload failed')
        return error_response('server_error', 'Could not upload image.', 500)
    return jsonify({'url': url})


@creator_studio_bp.post('/uploads/audio')
@require_auth
def upload_audio(user):
    _, err = _require_creator(user)
    if err:
        return err
    fs = request.files.get('file')
    if not fs:
        return validation_failed('file is required (multipart upload).')
    try:
        url, public_id = upload_audio_file(fs)
    except UploadError as e:
        return error_response(e.code, e.message, e.status)
    except Exception:
        log.exception('Audio upload failed')
        return error_response('server_error', 'Could not upload audio.', 500)
    return jsonify({'url': url, 'cloudinary_public_id': public_id})
