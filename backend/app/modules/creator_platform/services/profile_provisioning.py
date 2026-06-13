"""Creator profile provisioning — Stage 5 §5.2.

CreatorPlatform's spec describes a native apply→approve flow. ZimHub overrides
it: the Stage-1 `seller_signup_requests` system is the single front door for ALL
seller types, including creators. The signup-request approve route already flips
`is_creator=true` and creates the bare `creator_profile` shell
(`_ensure_profile_shell`). This module is the second half: it populates the
CreatorPlatform-expected fields on that shell and marks it approved.

Net effect: a creator applies at /sell/creator, a Super Admin approves in the
same inbox as every other seller, and `provision_creator_profile` fills in the
profile so Creator Studio + the public page work immediately — no separate
CreatorPlatform onboarding.
"""
import logging

from extensions import db
from app.models import CreatorProfile
from app.utils.slugify import slugify_unique
from app.services import host

from ..types import CREATOR_TYPES

log = logging.getLogger('zimhub.creator_platform.provisioning')

# A small palette of pleasant default accents, picked deterministically so each
# new creator gets a distinct-but-on-brand colour without a picker decision.
_DEFAULT_ACCENTS = [
    '#7c3aed',  # violet (section default)
    '#db2777',  # pink
    '#0891b2',  # cyan
    '#d97706',  # amber
    '#16a34a',  # green
    '#dc2626',  # red
]


def _pick_accent(seed_str: str) -> str:
    h = sum(ord(c) for c in (seed_str or 'x'))
    return _DEFAULT_ACCENTS[h % len(_DEFAULT_ACCENTS)]


def provision_creator_profile(user, category_payload: dict | None):
    """Populate the creator_profile for a freshly-approved creator.

    Idempotent: safe to call on an already-provisioned profile (only fills
    blanks; never clobbers creator-set customisation). Returns the profile.
    """
    payload = category_payload or {}
    # Query directly rather than via user.creator_profile: the signup-approve
    # flow created the shell moments earlier in this same session, and the
    # relationship attribute can still be a cached None — using it would insert a
    # SECOND profile and collide on the user_id primary key.
    profile = CreatorProfile.query.filter_by(user_id=user.id).first()
    if profile is None:
        # The shell should already exist (signup approve calls
        # _ensure_profile_shell first). Defend: build a minimal one.
        display_name = (payload.get('display_name')
                        or user.name)
        slug = slugify_unique(
            display_name,
            exists_fn=lambda s: db.session.query(CreatorProfile.user_id)
                                  .filter_by(creator_slug=s).first() is not None,
        )
        profile = CreatorProfile(
            user_id=user.id, display_name=display_name, creator_slug=slug,
        )
        db.session.add(profile)
        db.session.flush()

    # --- creator_types (validated against the registry) -------------------
    raw_types = payload.get('creator_types') or list(profile.creator_types or [])
    if isinstance(raw_types, str):
        raw_types = [raw_types]
    clean_types = [t for t in raw_types if t in CREATOR_TYPES]
    if not clean_types:
        clean_types = ['musician']  # sensible default; documented
    profile.creator_types = clean_types

    # --- discipline tags ---------------------------------------------------
    tags = payload.get('discipline_tags') or list(profile.discipline_tags or [])
    if isinstance(tags, str):
        tags = [tags]
    profile.discipline_tags = list(tags)

    # --- defaults that the creator can later customise --------------------
    if not profile.accent_color:
        profile.accent_color = _pick_accent(profile.creator_slug or user.name)
    if not profile.module_order:
        profile.module_order = {'order': []}
    if profile.bio is None and payload.get('bio'):
        profile.bio = str(payload['bio'])[:1000]

    # Social / external links from the application payload, if provided.
    social = payload.get('social_links')
    if isinstance(social, dict) and not (profile.social_links or {}):
        profile.social_links = social
    external = payload.get('external_links')
    if isinstance(external, dict) and not (profile.external_links or {}):
        profile.external_links = external

    # The host already gated approval via the signup request, so at provision
    # time the CreatorPlatform-internal status is always 'approved'.
    profile.status = 'approved'

    db.session.flush()
    log.info('[CREATOR PROVISION] user=%s slug=%s types=%s',
             user.id, profile.creator_slug, profile.creator_types)

    # On-platform welcome (in addition to the generic seller-approved notice).
    try:
        host.notify(
            user.id, 'creator_studio_ready',
            'Your Creator Studio is ready',
            'Your creator profile is live. Open Creator Studio to upload music, '
            'build galleries, and publish events.',
            metadata={'creator_slug': profile.creator_slug},
        )
    except Exception:  # notifications are best-effort here
        log.exception('creator welcome notify failed (non-fatal)')

    return profile
