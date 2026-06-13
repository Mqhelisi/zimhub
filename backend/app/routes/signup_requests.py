"""Signup requests — per spec §5.2.

Public:
    POST /api/signup-requests

Super admin:
    GET  /api/super/signup-requests?status=&category=&q=
    GET  /api/super/signup-requests/:id
    POST /api/super/signup-requests/:id/approve
    POST /api/super/signup-requests/:id/reject

Approval creates (or attaches to) a User, flips the capability flag on, creates
the matching profile shell, generates a temp password, dispatches credentials,
and emits the seller_application_approved notification.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func

from extensions import db
from app.models import (
    User,
    SellerSignupRequest,
    SalesmanProfile,
    PromoterProfile,
    ProviderProfile,
    CreatorProfile,
)
from app.services import host
from app.services.notification_service import (
    notify_new_signup_request,
    notify_seller_application_approved,
    notify_seller_application_rejected,
)
from app.services.mock_transport import (
    dispatch_approval_credentials,
    dispatch_rejection_email,
)
from app.utils.decorators import require_role
from app.utils.errors import validation_failed, not_found, conflict
from app.utils.phone import normalise_phone, is_valid_phone
from app.utils.slugify import slugify_unique
from app.utils.passwords import hash_password, generate_temp_password


signup_bp = Blueprint('signup_requests', __name__)


CATEGORIES = ('salesman', 'promoter', 'provider', 'creator')

CAPABILITY_FLAG_BY_CATEGORY = {
    'salesman': 'is_salesman',
    'promoter': 'is_promoter',
    'provider': 'is_provider',
    'creator':  'is_creator',
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate_application_payload(data: dict) -> tuple[dict, dict]:
    """Return (clean, errors). errors empty means valid."""
    errors = {}
    clean = {}

    category = (data.get('category') or '').strip().lower()
    if category not in CATEGORIES:
        errors['category'] = 'Must be one of: ' + ', '.join(CATEGORIES)
    clean['category'] = category

    for field in ('full_name', 'email', 'phone', 'suburb', 'pitch'):
        raw = (data.get(field) or '').strip() if isinstance(data.get(field), str) else data.get(field)
        if not raw:
            errors[field] = f'{field.replace("_", " ").title()} is required'
        clean[field] = raw

    if clean.get('pitch') and len(clean['pitch']) > 500:
        errors['pitch'] = 'Pitch must be 500 characters or fewer'

    if clean.get('email') and '@' not in clean['email']:
        errors['email'] = 'A valid email address is required'

    if clean.get('phone'):
        if not is_valid_phone(clean['phone']):
            errors['phone'] = 'A valid Zimbabwean phone is required (e.g. +263772123456 or 0772123456)'
        else:
            clean['phone'] = normalise_phone(clean['phone'])

    business_name = (data.get('business_name') or '').strip() if isinstance(data.get('business_name'), str) else None
    clean['business_name'] = business_name or None

    payload = data.get('category_payload') or {}
    if not isinstance(payload, dict):
        errors['category_payload'] = 'Must be an object'
        payload = {}
    payload_errors = _validate_category_payload(category, payload)
    if payload_errors:
        for k, v in payload_errors.items():
            errors[f'category_payload.{k}'] = v
    clean['category_payload'] = payload

    return clean, errors


def _validate_category_payload(category: str, payload: dict) -> dict:
    """Return {field: 'reason', ...}."""
    errors = {}
    if category == 'salesman':
        for f in ('shop_name', 'primary_category', 'sample_products', 'pickup_delivery_preference'):
            if not payload.get(f):
                errors[f] = f'{f.replace("_", " ").title()} is required'
    elif category == 'promoter':
        cats = payload.get('event_categories') or []
        if not isinstance(cats, list) or not cats:
            errors['event_categories'] = 'At least one event category is required'
    elif category == 'provider':
        if not payload.get('trade'):
            errors['trade'] = 'Trade is required'
        if payload.get('years_experience') is None or payload.get('years_experience') == '':
            errors['years_experience'] = 'Years of experience is required'
        if not payload.get('pricing_unit_preference'):
            errors['pricing_unit_preference'] = 'Pricing unit preference is required'
        areas = payload.get('service_areas') or []
        if not isinstance(areas, list) or not areas:
            errors['service_areas'] = 'At least one service area is required'
    elif category == 'creator':
        types = payload.get('creator_types') or []
        if not isinstance(types, list) or not types:
            errors['creator_types'] = 'At least one creator type is required'
    return errors


# ---------------------------------------------------------------------------
# Public submission
# ---------------------------------------------------------------------------
@signup_bp.post('/api/signup-requests')
def submit_signup_request():
    data = request.get_json(silent=True) or {}
    clean, errors = _validate_application_payload(data)
    if errors:
        return validation_failed('Please fix the highlighted fields.', field_errors=errors)

    req = SellerSignupRequest(
        category=clean['category'],
        full_name=clean['full_name'],
        business_name=clean.get('business_name'),
        email=clean['email'].lower(),
        phone=clean['phone'],
        suburb=clean['suburb'],
        pitch=clean['pitch'],
        category_payload=clean['category_payload'],
        status='pending',
    )
    db.session.add(req)
    db.session.flush()

    notify_new_signup_request(req)
    db.session.commit()

    return jsonify({'ok': True, 'request_id': str(req.id)}), 201


# ---------------------------------------------------------------------------
# Super admin — list + detail
# ---------------------------------------------------------------------------
@signup_bp.get('/api/super/signup-requests')
@require_role('super_admin')
def list_signup_requests(user: User):
    status = request.args.get('status')
    category = request.args.get('category')
    q = (request.args.get('q') or '').strip()

    query = SellerSignupRequest.query
    if status:
        query = query.filter(SellerSignupRequest.status == status)
    if category:
        query = query.filter(SellerSignupRequest.category == category)
    if q:
        like = f'%{q.lower()}%'
        query = query.filter(or_(
            func.lower(SellerSignupRequest.full_name).like(like),
            func.lower(SellerSignupRequest.business_name).like(like),
            func.lower(SellerSignupRequest.email).like(like),
        ))

    requests_list = query.order_by(SellerSignupRequest.created_at.desc()).limit(200).all()

    # Counts across the whole table (not the filtered query) so the UI tabs
    # can show consistent totals.
    counts_rows = db.session.query(
        SellerSignupRequest.status, func.count(SellerSignupRequest.id)
    ).group_by(SellerSignupRequest.status).all()
    counts = {'pending': 0, 'approved': 0, 'rejected': 0}
    for s, n in counts_rows:
        counts[s] = n

    return jsonify({
        'requests': [r.to_dict() for r in requests_list],
        'counts': counts,
    })


@signup_bp.get('/api/super/signup-requests/<uuid:req_id>')
@require_role('super_admin')
def get_signup_request(user: User, req_id):
    req = db.session.get(SellerSignupRequest, req_id)
    if not req:
        return not_found('Application not found.')
    return jsonify({'request': req.to_dict()})


# ---------------------------------------------------------------------------
# Approve
# ---------------------------------------------------------------------------
@signup_bp.post('/api/super/signup-requests/<uuid:req_id>/approve')
@require_role('super_admin')
def approve_signup_request(user: User, req_id):
    req = db.session.get(SellerSignupRequest, req_id)
    if not req:
        return not_found('Application not found.')
    if req.status != 'pending':
        return conflict(f'This application is already {req.status}.')

    body = request.get_json(silent=True) or {}
    channels = body.get('credential_delivery_channels') or ['email']
    if 'email' not in channels:
        # Per spec — email is the default-checked option. We require at least one channel.
        if not channels:
            return validation_failed('Pick at least one delivery channel.')
    channels = [c for c in channels if c in ('email', 'whatsapp', 'sms')]
    if not channels:
        return validation_failed('Pick at least one delivery channel.')

    capability_flag = CAPABILITY_FLAG_BY_CATEGORY[req.category]

    # Either attach to an existing user (matching email) or create a new one.
    target_user = User.query.filter_by(email=req.email.lower()).first()
    temp_password = generate_temp_password()
    created_new = False
    if target_user is None:
        target_user = User(
            email=req.email.lower(),
            phone=req.phone,
            password_hash=hash_password(temp_password),
            name=req.full_name,
            suburb=req.suburb,
            city='Bulawayo',
            is_buyer=True,
            password_reset_required=True,
        )
        db.session.add(target_user)
        db.session.flush()
        created_new = True
    else:
        # Existing user: reset their password to the new temp and flag for forced change.
        target_user.password_hash = hash_password(temp_password)
        target_user.password_reset_required = True

    # Flip the capability flag and create the profile shell.
    setattr(target_user, capability_flag, True)
    _ensure_profile_shell(target_user, req.category, req)

    # Stage 5 §5.2 — consolidate CreatorPlatform's apply-approve into this inbox.
    # After the shell exists, populate the CreatorPlatform-expected fields.
    if req.category == 'creator':
        from app.modules.creator_platform.services.profile_provisioning import (
            provision_creator_profile,
        )
        provision_creator_profile(target_user, req.category_payload)

    req.status = 'approved'
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.created_user_id = target_user.id

    # Dispatch credentials via the requested channels.
    dispatch_approval_credentials(
        recipient_email=target_user.email,
        recipient_phone=target_user.phone,
        channels=channels,
        full_name=target_user.name,
        category=req.category,
        temp_password=temp_password,
    )

    # On-platform notification for the new seller.
    notify_seller_application_approved(
        target_user,
        category=req.category,
        temp_password=temp_password,
    )

    db.session.commit()

    return jsonify({
        'ok': True,
        'user_id': str(target_user.id),
        'temp_password': temp_password,
        'created_new_user': created_new,
        'delivery_channels': channels,
    })


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------
@signup_bp.post('/api/super/signup-requests/<uuid:req_id>/reject')
@require_role('super_admin')
def reject_signup_request(user: User, req_id):
    req = db.session.get(SellerSignupRequest, req_id)
    if not req:
        return not_found('Application not found.')
    if req.status != 'pending':
        return conflict(f'This application is already {req.status}.')

    body = request.get_json(silent=True) or {}
    reason = (body.get('reason') or '').strip()
    if not reason:
        return validation_failed('A rejection reason is required.', field_errors={'reason': 'Required'})

    req.status = 'rejected'
    req.rejection_reason = reason
    req.reviewed_by = user.id
    req.reviewed_at = datetime.now(timezone.utc)

    # Dispatch rejection email.
    dispatch_rejection_email(
        recipient_email=req.email,
        full_name=req.full_name,
        category=req.category,
        reason=reason,
    )

    # If the applicant happens to already have a user account, attach an
    # on-platform notification too. Otherwise the email is the only channel.
    existing = User.query.filter_by(email=req.email.lower()).first()
    if existing:
        notify_seller_application_rejected(
            existing, category=req.category, reason=reason
        )

    db.session.commit()
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Profile shell creation
# ---------------------------------------------------------------------------
def _ensure_profile_shell(user: User, category: str, source_request: SellerSignupRequest = None):
    """Create the matching profile shell if it doesn't exist.

    Called by both signup-request approval and the super-admin capability toggle
    (with source_request=None for the toggle case — uses placeholder fields).
    """
    payload = (source_request.category_payload if source_request else {}) or {}

    if category == 'salesman' and not user.salesman_profile:
        shop_name = payload.get('shop_name') or (source_request.business_name if source_request else None) or user.name
        slug = slugify_unique(
            shop_name,
            exists_fn=lambda s: db.session.query(SalesmanProfile.user_id).filter_by(shop_slug=s).first() is not None,
        )
        profile = SalesmanProfile(
            user_id=user.id,
            shop_name=shop_name,
            shop_slug=slug,
            pickup_delivery_policy=payload.get('pickup_delivery_preference'),
        )
        db.session.add(profile)

    elif category == 'promoter' and not user.promoter_profile:
        profile = PromoterProfile(
            user_id=user.id,
            organisation_name=payload.get('organisation_name') or (source_request.business_name if source_request else None),
        )
        db.session.add(profile)

    elif category == 'provider' and not user.provider_profile:
        trade = payload.get('trade') or 'general'
        areas = payload.get('service_areas') or []
        if isinstance(areas, str):
            areas = [areas]
        profile = ProviderProfile(
            user_id=user.id,
            trade=trade,
            suburbs_served=list(areas),
        )
        db.session.add(profile)

    elif category == 'creator' and not user.creator_profile:
        display_name = (source_request.business_name if source_request else None) or user.name
        slug = slugify_unique(
            display_name,
            exists_fn=lambda s: db.session.query(CreatorProfile.user_id).filter_by(creator_slug=s).first() is not None,
        )
        types = payload.get('creator_types') or []
        if isinstance(types, str):
            types = [types]
        tags = payload.get('discipline_tags') or []
        if isinstance(tags, str):
            tags = [tags]
        profile = CreatorProfile(
            user_id=user.id,
            display_name=display_name,
            creator_slug=slug,
            creator_types=list(types),
            discipline_tags=list(tags),
        )
        db.session.add(profile)

    db.session.flush()
