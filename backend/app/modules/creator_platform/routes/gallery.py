"""Gallery management routes — CreatorPlatform_Spec.md §5.3 / §6. Auth + is_creator.

  GET    /api/creator/gallery                       own collections (+items)
  POST   /api/creator/gallery/collections           create a collection
  PATCH  /api/creator/gallery/collections/:id       edit collection
  DELETE /api/creator/gallery/collections/:id        delete collection (+items)
  POST   /api/creator/gallery/items                  add an image (image_url from /uploads/image)
  PATCH  /api/creator/gallery/items/:id              edit item / visibility
  DELETE /api/creator/gallery/items/:id              delete item
"""
import logging

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import forbidden, validation_failed, not_found

from ..models import GalleryCollection, GalleryItem, GALLERY_CATEGORIES

log = logging.getLogger('zimhub.creator_platform.gallery')

gallery_bp = Blueprint('creator_platform_gallery', __name__,
                       url_prefix='/api/creator/gallery')


def _require_creator(user):
    if not user.is_creator:
        return None, forbidden('You need a Creator capability to access this.')
    if user.creator_profile is None:
        return None, forbidden('Your creator profile is not provisioned yet.')
    return user.creator_profile, None


@gallery_bp.get('')
@gallery_bp.get('/')
@require_auth
def list_gallery(user):
    profile, err = _require_creator(user)
    if err:
        return err
    cols = (GalleryCollection.query
            .filter(GalleryCollection.creator_id == profile.user_id)
            .order_by(GalleryCollection.created_at.asc()).all())
    return jsonify({'collections': [c.to_dict(include_items=True) for c in cols]})


@gallery_bp.post('/collections')
@require_auth
def create_collection(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return validation_failed('Some fields are invalid.',
                                 field_errors={'title': 'Required.'})
    c = GalleryCollection(
        creator_id=profile.user_id, title=title[:200],
        description=(data.get('description') or '').strip() or None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify({'collection': c.to_dict(include_items=True)}), 201


@gallery_bp.patch('/collections/<col_id>')
@require_auth
def edit_collection(user, col_id):
    profile, err = _require_creator(user)
    if err:
        return err
    c = db.session.get(GalleryCollection, col_id)
    if not c or str(c.creator_id) != str(profile.user_id):
        return not_found('Collection not found.')
    data = request.get_json(silent=True) or {}
    if 'title' in data:
        v = (data.get('title') or '').strip()
        if v:
            c.title = v[:200]
    if 'description' in data:
        c.description = (data.get('description') or '').strip() or None
    db.session.commit()
    return jsonify({'collection': c.to_dict(include_items=True)})


@gallery_bp.delete('/collections/<col_id>')
@require_auth
def delete_collection(user, col_id):
    profile, err = _require_creator(user)
    if err:
        return err
    c = db.session.get(GalleryCollection, col_id)
    if not c or str(c.creator_id) != str(profile.user_id):
        return not_found('Collection not found.')
    db.session.delete(c)  # cascade removes items
    db.session.commit()
    return jsonify({'ok': True})


@gallery_bp.post('/items')
@require_auth
def create_item(user):
    profile, err = _require_creator(user)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    field_errors = {}
    title = (data.get('title') or '').strip()
    image_url = (data.get('image_url') or '').strip()
    if not title:
        field_errors['title'] = 'Required.'
    if not image_url:
        field_errors['image_url'] = 'Upload an image first.'
    category = (data.get('category') or '').strip().lower() or None
    if category and category not in GALLERY_CATEGORIES:
        field_errors['category'] = f'Must be one of: {", ".join(GALLERY_CATEGORIES)}.'
    collection_id = data.get('collection_id') or None
    if collection_id:
        col = db.session.get(GalleryCollection, collection_id)
        if not col or str(col.creator_id) != str(profile.user_id):
            field_errors['collection_id'] = 'Unknown collection.'
    if field_errors:
        return validation_failed('Some fields are invalid.', field_errors=field_errors)

    year = data.get('year_created')
    item = GalleryItem(
        creator_id=profile.user_id,
        collection_id=collection_id,
        title=title[:200],
        description=(data.get('description') or '').strip() or None,
        category=category,
        year_created=year if isinstance(year, int) else None,
        image_url=image_url,
        cloudinary_public_id=(data.get('cloudinary_public_id') or '').strip() or None,
        is_visible=True,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'item': item.to_dict()}), 201


@gallery_bp.patch('/items/<item_id>')
@require_auth
def edit_item(user, item_id):
    profile, err = _require_creator(user)
    if err:
        return err
    item = db.session.get(GalleryItem, item_id)
    if not item or str(item.creator_id) != str(profile.user_id):
        return not_found('Item not found.')
    data = request.get_json(silent=True) or {}
    if 'title' in data:
        v = (data.get('title') or '').strip()
        if v:
            item.title = v[:200]
    if 'description' in data:
        item.description = (data.get('description') or '').strip() or None
    if 'category' in data:
        cat = (data.get('category') or '').strip().lower() or None
        if cat and cat not in GALLERY_CATEGORIES:
            return validation_failed('Some fields are invalid.',
                                     field_errors={'category': 'Invalid category.'})
        item.category = cat
    if 'is_visible' in data:
        item.is_visible = bool(data['is_visible'])
    db.session.commit()
    return jsonify({'item': item.to_dict()})


@gallery_bp.delete('/items/<item_id>')
@require_auth
def delete_item(user, item_id):
    profile, err = _require_creator(user)
    if err:
        return err
    item = db.session.get(GalleryItem, item_id)
    if not item or str(item.creator_id) != str(profile.user_id):
        return not_found('Item not found.')
    db.session.delete(item)
    db.session.commit()
    return jsonify({'ok': True})
