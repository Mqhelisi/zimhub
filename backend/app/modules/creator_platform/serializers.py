"""Public creator-page serializer — type-aware composition (CreatorPlatform §5.1).

Builds the full payload a public creator page renders: profile + the union of
type-driven modules (music for Musicians, gallery for Photographers / Visual
Artists) + events. The frontend reads `modules` (ordered list of module keys)
to decide section ordering; a Musician leads with music, a Photographer with
gallery, a multi-type creator gets both.
"""
from datetime import datetime, timezone

from extensions import db
from app.models import User
from .types import modules_for_types, is_musician, has_gallery
from .models import Track, GalleryCollection, CreatorEvent
from app.modules.ticket_generator.models import Event


def _ordered_modules(profile):
    """Resolve the page module order: creator-customised order first (filtered
    to what their types unlock), then any remaining unlocked modules."""
    unlocked = modules_for_types(profile.creator_types)
    custom = ((profile.module_order or {}).get('order') or [])
    ordered = [m for m in custom if m in unlocked]
    for m in unlocked:
        if m not in ordered:
            ordered.append(m)
    return ordered


def creator_card(profile):
    """Compact card for discovery surfaces."""
    return {
        'user_id': str(profile.user_id),
        'display_name': profile.display_name,
        'creator_slug': profile.creator_slug,
        'creator_types': list(profile.creator_types or []),
        'discipline_tags': list(profile.discipline_tags or []),
        'accent_color': profile.accent_color,
        'hero_image_url': profile.hero_image_url,
        'photo_url': profile.photo_url,
        'bio': profile.bio,
    }


def public_creator_payload(profile):
    """Full type-aware page payload for /api/creators/:slug."""
    types = list(profile.creator_types or [])
    data = {
        **creator_card(profile),
        'social_links': profile.social_links or {},
        'external_links': profile.external_links or {},
        'contact_email': profile.contact_email if profile.contact_email_public else None,
        'modules': _ordered_modules(profile),
    }

    # Music module (Musician)
    if is_musician(types):
        tracks = (Track.query
                  .filter(Track.creator_id == profile.user_id,
                          Track.is_visible.is_(True))
                  .order_by(Track.position.asc(), Track.uploaded_at.desc())
                  .all())
        data['tracks'] = [t.to_dict() for t in tracks]
    else:
        data['tracks'] = []

    # Gallery module (Photographer / Visual Artist)
    if has_gallery(types):
        collections = (GalleryCollection.query
                       .filter(GalleryCollection.creator_id == profile.user_id)
                       .order_by(GalleryCollection.created_at.asc())
                       .all())
        data['collections'] = [c.to_dict(include_items=True) for c in collections]
    else:
        data['collections'] = []

    # Events module (all creators): native creator_events + the linked TG event
    now = datetime.now(timezone.utc)
    cevents = (CreatorEvent.query
               .filter(CreatorEvent.creator_id == profile.user_id,
                       CreatorEvent.status == 'approved')
               .order_by(CreatorEvent.event_date.asc())
               .all())
    events_out = []
    for ce in cevents:
        row = ce.to_dict(include_host_event=True)
        events_out.append(row)
    data['events'] = events_out

    return data


def discovery_list(type_filter=None, q=None):
    """List approved creators for /api/creators, optional type + text filter."""
    from app.models import CreatorProfile
    query = (db.session.query(CreatorProfile)
             .join(User, User.id == CreatorProfile.user_id)
             .filter(CreatorProfile.status == 'approved',
                     User.status != 'suspended'))
    rows = query.order_by(CreatorProfile.created_at.asc()).limit(200).all()
    out = []
    for p in rows:
        if type_filter and type_filter not in (p.creator_types or []):
            continue
        if q:
            ql = q.lower()
            hay = ' '.join([
                p.display_name or '', ' '.join(p.discipline_tags or []),
                ' '.join(p.creator_types or []),
            ]).lower()
            if ql not in hay:
                continue
        out.append(creator_card(p))
    return out
