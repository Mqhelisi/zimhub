"""Provider admin — /api/provider/* (Stage 4 spec §5.2.2).

All endpoints require auth + user.is_provider; identity from JWT cookie, no
:user_id parameter.

Profile note: BI spec also names GET/PUT /api/provider/profile (profile +
booking settings). One URL can have one owner, so this module serves a MERGED
payload — the host provider_profiles fields (trade, bio, photo, suburbs) plus
the BI-owned settings (display_name, timezone, rates, response/cancel rules)
— satisfying both specs' purpose with a single endpoint.

Availability and time-block CRUD are owned by BookingInterface; the
AvailabilityManager UI calls BI's endpoints directly — not proxied here.
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_role
from app.utils.errors import validation_failed, not_found, error_response
from app.utils.slugify import slugify_unique
from app.models import ProviderProfile
from app.modules.shop.uploads import upload_image_file, UploadError
from app.modules.booking_interface.models import BIProviderProfile, Booking
from app.modules.booking_interface.services import booking_label

from ..models import ProviderService, PRICING_UNITS, TRADES


log = logging.getLogger('zimhub.services_section.provider_admin')

provider_admin_bp = Blueprint('services_section_provider_admin', __name__,
                              url_prefix='/api/provider')


def _now():
    return datetime.now(dt_timezone.utc)


def ensure_bi_profile(user) -> BIProviderProfile:
    """Lazily create the BI profile shell for any is_provider user (covers
    super-admin promotions: acceptance step 73)."""
    prof = BIProviderProfile.query.filter_by(provider_id=user.id).first()
    if prof:
        return prof
    host_prof = getattr(user, 'provider_profile', None)
    display = user.name
    tz = (host_prof.timezone if host_prof and host_prof.timezone else 'Africa/Harare')
    slug = slugify_unique(
        display,
        exists_fn=lambda s: db.session.query(BIProviderProfile.id)
        .filter_by(slug=s).first() is not None,
    )
    prof = BIProviderProfile(provider_id=user.id, display_name=display,
                             slug=slug, bio=(host_prof.bio if host_prof else None),
                             timezone=tz)
    db.session.add(prof)
    db.session.flush()
    return prof


def _merged_profile(user, bi_prof: BIProviderProfile):
    host_prof = getattr(user, 'provider_profile', None)
    d = bi_prof.to_dict()
    d.update({
        'trade': host_prof.trade if host_prof else None,
        'photo_url': host_prof.photo_url if host_prof else None,
        'suburbs_served': list(host_prof.suburbs_served or []) if host_prof else [],
        'bio': bi_prof.bio or (host_prof.bio if host_prof else None),
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
    })
    return d


# ----------------------------------------------------------------------
# Profile (merged host + BI settings)
# ----------------------------------------------------------------------
@provider_admin_bp.get('/profile')
@require_role('provider')
def get_profile(user):
    bi_prof = ensure_bi_profile(user)
    db.session.commit()
    return jsonify({'profile': _merged_profile(user, bi_prof)})


@provider_admin_bp.put('/profile')
@require_role('provider')
def update_profile(user):
    data = request.get_json(silent=True) or {}
    bi_prof = ensure_bi_profile(user)
    host_prof = getattr(user, 'provider_profile', None)
    if host_prof is None:
        host_prof = ProviderProfile(user_id=user.id,
                                    trade=data.get('trade') or 'Other')
        db.session.add(host_prof)

    if 'trade' in data:
        trade = (data.get('trade') or '').strip()
        if trade not in TRADES:
            return validation_failed(f"trade must be one of: {', '.join(TRADES)}.")
        host_prof.trade = trade
    if 'bio' in data:
        bio = (data.get('bio') or '').strip() or None
        host_prof.bio = bio
        bi_prof.bio = bio
    if 'photo_url' in data:
        host_prof.photo_url = (data.get('photo_url') or '').strip() or None
    if 'suburbs_served' in data:
        subs = data.get('suburbs_served')
        if not isinstance(subs, list):
            return validation_failed('suburbs_served must be a list.')
        host_prof.suburbs_served = [str(s).strip() for s in subs if str(s).strip()]

    if 'display_name' in data:
        name = (data.get('display_name') or '').strip()
        if not name:
            return validation_failed('display_name cannot be empty.')
        bi_prof.display_name = name
    for int_field in ('min_hours', 'max_hours', 'response_hours', 'cancel_cutoff_hours'):
        if int_field in data:
            v = data.get(int_field)
            if v is None and int_field != 'cancel_cutoff_hours':
                setattr(bi_prof, int_field, None)
                continue
            try:
                iv = int(v)
            except (TypeError, ValueError):
                return validation_failed(f'{int_field} must be an integer.')
            if iv < 0:
                return validation_failed(f'{int_field} must be >= 0.')
            setattr(bi_prof, int_field, iv)
    if 'hourly_rate_usd' in data:
        v = data.get('hourly_rate_usd')
        if v is None or v == '':
            bi_prof.hourly_rate_usd = None
        else:
            try:
                dv = Decimal(str(v))
            except InvalidOperation:
                return validation_failed('hourly_rate_usd must be a number.')
            if dv < 0:
                return validation_failed('hourly_rate_usd must be >= 0.')
            bi_prof.hourly_rate_usd = dv
    if 'timezone' in data and (data.get('timezone') or '').strip():
        bi_prof.timezone = data['timezone'].strip()

    db.session.commit()
    return jsonify({'profile': _merged_profile(user, bi_prof)})


# ----------------------------------------------------------------------
# Services CRUD
# ----------------------------------------------------------------------
def _validate_service_payload(data, partial=False):
    errors = {}
    out = {}
    if 'name' in data or not partial:
        name = (data.get('name') or '').strip()
        if not name:
            errors['name'] = 'Name is required.'
        elif len(name) > 200:
            errors['name'] = 'Name must be at most 200 characters.'
        else:
            out['name'] = name
    if 'description' in data or not partial:
        desc = (data.get('description') or '').strip()
        if not desc:
            errors['description'] = 'Description is required.'
        else:
            out['description'] = desc
    if 'pricing_unit' in data or not partial:
        unit = (data.get('pricing_unit') or '').strip()
        if unit not in PRICING_UNITS:
            errors['pricing_unit'] = f"Must be one of: {', '.join(PRICING_UNITS)}."
        else:
            out['pricing_unit'] = unit
    if 'rate_usd' in data or not partial:
        try:
            rate = Decimal(str(data.get('rate_usd')))
            if rate < 0:
                errors['rate_usd'] = 'Rate must be >= 0.'
            else:
                out['rate_usd'] = rate
        except (InvalidOperation, TypeError):
            errors['rate_usd'] = 'Rate must be a number.'
    if 'default_duration_minutes' in data:
        v = data.get('default_duration_minutes')
        if v in (None, ''):
            out['default_duration_minutes'] = None
        else:
            try:
                iv = int(v)
                if iv <= 0:
                    errors['default_duration_minutes'] = 'Must be a positive number of minutes.'
                else:
                    out['default_duration_minutes'] = iv
            except (TypeError, ValueError):
                errors['default_duration_minutes'] = 'Must be a number of minutes.'
    if 'status' in data:
        st = (data.get('status') or '').strip()
        if st not in ('active', 'archived'):
            errors['status'] = "Status must be 'active' or 'archived'."
        else:
            out['status'] = st
    return out, errors


@provider_admin_bp.get('/services')
@require_role('provider')
def list_services(user):
    q = ProviderService.query.filter_by(provider_user_id=user.id)
    status = (request.args.get('status') or '').strip()
    if status in ('active', 'archived'):
        q = q.filter(ProviderService.status == status)
    term = (request.args.get('q') or '').strip()
    if term:
        q = q.filter(ProviderService.name.ilike(f'%{term}%'))
    rows = q.order_by(ProviderService.created_at.desc()).all()
    return jsonify({'services': [s.to_dict() for s in rows]})


@provider_admin_bp.post('/services')
@require_role('provider')
def create_service(user):
    data = request.get_json(silent=True) or {}
    fields, errors = _validate_service_payload(data, partial=False)
    if errors:
        return validation_failed(field_errors=errors)
    svc = ProviderService(provider_user_id=user.id, **fields)
    db.session.add(svc)
    db.session.commit()
    return jsonify({'service': svc.to_dict()}), 201


@provider_admin_bp.get('/services/<uuid:service_id>')
@require_role('provider')
def get_service(user, service_id):
    svc = db.session.get(ProviderService, service_id)
    if not svc or str(svc.provider_user_id) != str(user.id):
        return not_found('Service not found.')
    return jsonify({'service': svc.to_dict()})


@provider_admin_bp.put('/services/<uuid:service_id>')
@require_role('provider')
def update_service(user, service_id):
    svc = db.session.get(ProviderService, service_id)
    if not svc or str(svc.provider_user_id) != str(user.id):
        return not_found('Service not found.')
    data = request.get_json(silent=True) or {}
    fields, errors = _validate_service_payload(data, partial=True)
    if errors:
        return validation_failed(field_errors=errors)
    for k, v in fields.items():
        setattr(svc, k, v)
    db.session.commit()
    return jsonify({'service': svc.to_dict()})


@provider_admin_bp.delete('/services/<uuid:service_id>')
@require_role('provider')
def archive_service(user, service_id):
    """Soft-delete: sets status='archived'. Never hard-deletes — historic
    bookings reference the row via bookable_id."""
    svc = db.session.get(ProviderService, service_id)
    if not svc or str(svc.provider_user_id) != str(user.id):
        return not_found('Service not found.')
    svc.status = 'archived'
    db.session.commit()
    return jsonify({'ok': True})


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------
@provider_admin_bp.get('/dashboard')
@require_role('provider')
def dashboard(user):
    ensure_bi_profile(user)
    db.session.commit()
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    pending = Booking.query.filter_by(provider_id=user.id, status='requested').count()
    todays = (Booking.query
              .filter(Booking.provider_id == user.id, Booking.status == 'confirmed',
                      Booking.start_at >= today_start, Booking.start_at < today_end)
              .order_by(Booking.start_at).all())
    week = Booking.query.filter(
        Booking.provider_id == user.id, Booking.status == 'confirmed',
        Booking.start_at >= today_start, Booking.start_at < week_end).count()
    active_services = ProviderService.query.filter_by(
        provider_user_id=user.id, status='active').count()

    recent = (Booking.query
              .filter(Booking.provider_id == user.id)
              .order_by(Booking.created_at.desc())
              .limit(8).all())

    return jsonify({
        'stats': {
            'pending_requests': pending,
            'todays_bookings': len(todays),
            'week_bookings': week,
            'services_active': active_services,
        },
        'recent_requests': [b.to_dict(viewer=user, label=booking_label(b))
                            for b in recent],
        'todays_calendar': [b.to_dict(viewer=user, label=booking_label(b))
                            for b in todays],
    })


# ----------------------------------------------------------------------
# Image upload (reuses Stage 2 Cloudinary/local pattern)
# ----------------------------------------------------------------------
@provider_admin_bp.post('/uploads/image')
@require_role('provider')
def upload_image(user):
    fs = request.files.get('file')
    try:
        url = upload_image_file(fs)
    except UploadError as e:
        return error_response(e.code, e.message, e.status)
    return jsonify({'url': url}), 201
