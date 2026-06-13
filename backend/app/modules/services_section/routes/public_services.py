"""Public Services API — /api/services/* (Stage 4 spec §5.2.3).

Discovery rules: only active users (status='active') who are providers with
at least one active service are listed. Default sort: ranking score desc,
then name asc. q matches provider name / bio / service name ILIKE. Suburb
filtering is enabled HERE AND ONLY HERE (master spec §16.13).
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func

from extensions import db
from app.utils.errors import not_found, validation_failed
from app.models import User, ProviderProfile
from app.modules.booking_interface.models import BIProviderProfile, Booking
from app.modules.booking_interface.services import free_slots

from ..models import ProviderService, TRADES
from ..ranking import top_providers


log = logging.getLogger('zimhub.services_section.public')

public_services_bp = Blueprint('services_section_public', __name__,
                               url_prefix='/api/services')

PAGE_SIZE = 12


def _provider_card(user, completed_30d=None, service_count=None):
    host_prof = getattr(user, 'provider_profile', None)
    bi_prof = BIProviderProfile.query.filter_by(provider_id=user.id).first()
    if service_count is None:
        service_count = ProviderService.query.filter_by(
            provider_user_id=user.id, status='active').count()
    if completed_30d is None:
        since = datetime.now(dt_timezone.utc) - timedelta(days=30)
        completed_30d = Booking.query.filter(
            Booking.provider_id == user.id, Booking.status == 'completed',
            Booking.completed_at >= since).count()
    return {
        'user_id': str(user.id),
        'name': bi_prof.display_name if bi_prof else user.name,
        'slug': bi_prof.slug if bi_prof else None,
        'trade': host_prof.trade if host_prof else None,
        'bio': (bi_prof.bio if bi_prof and bi_prof.bio else
                (host_prof.bio if host_prof else None)),
        'photo_url': host_prof.photo_url if host_prof else None,
        'suburbs_served': list(host_prof.suburbs_served or []) if host_prof else [],
        'service_count': service_count,
        'completed_30d': completed_30d,
    }


def _active_provider_ids():
    """User ids that are listed: active provider users with ≥1 active service."""
    rows = (db.session.query(ProviderService.provider_user_id)
            .join(User, User.id == ProviderService.provider_user_id)
            .filter(ProviderService.status == 'active',
                    User.is_provider.is_(True), User.status == 'active')
            .distinct().all())
    return [r[0] for r in rows]


# ----------------------------------------------------------------------
@public_services_bp.get('/home')
def services_home():
    ranked = top_providers(limit=8)
    return jsonify({'top_providers': [
        _provider_card(u, completed_30d=c, service_count=s)
        for (u, c, s) in ranked
    ]})


# ----------------------------------------------------------------------
@public_services_bp.get('/providers')
def list_providers():
    trade = (request.args.get('trade') or '').strip()
    suburb = (request.args.get('suburb') or '').strip()
    term = (request.args.get('q') or '').strip()
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1

    listed_ids = _active_provider_ids()
    if not listed_ids:
        return jsonify({'providers': [], 'total': 0, 'page': 1,
                        'page_size': PAGE_SIZE,
                        'facets': {'trades': list(TRADES), 'suburbs': []}})

    q = (User.query
         .outerjoin(ProviderProfile, ProviderProfile.user_id == User.id)
         .filter(User.id.in_(listed_ids)))
    if trade:
        q = q.filter(ProviderProfile.trade == trade)
    if suburb:
        # Suburb filtering — Services-only per master spec §16.13.
        q = q.filter(ProviderProfile.suburbs_served.any(suburb))
    if term:
        like = f'%{term}%'
        matching_service_provider_ids = [
            r[0] for r in db.session.query(ProviderService.provider_user_id)
            .filter(ProviderService.status == 'active',
                    ProviderService.name.ilike(like)).distinct().all()
        ]
        q = q.filter(or_(
            User.name.ilike(like),
            ProviderProfile.bio.ilike(like),
            User.id.in_(matching_service_provider_ids or [None]),
        ))

    users = q.all()

    # Rank: top-providers score desc, then name asc (spec discovery rules).
    since = datetime.now(dt_timezone.utc) - timedelta(days=30)
    completed = dict(
        db.session.query(Booking.provider_id, func.count(Booking.id))
        .filter(Booking.status == 'completed', Booking.completed_at >= since)
        .group_by(Booking.provider_id).all())
    users.sort(key=lambda u: (-completed.get(u.id, 0), u.name.lower()))

    total = len(users)
    start = (page - 1) * PAGE_SIZE
    page_users = users[start:start + PAGE_SIZE]

    # Facets over the LISTED set (unfiltered) so chips stay stable.
    all_listed = User.query.filter(User.id.in_(listed_ids)).all()
    suburb_facet = sorted({
        s for u in all_listed
        for s in (getattr(u.provider_profile, 'suburbs_served', None) or [])
    })

    return jsonify({
        'providers': [_provider_card(u, completed_30d=completed.get(u.id, 0))
                      for u in page_users],
        'total': total, 'page': page, 'page_size': PAGE_SIZE,
        'facets': {'trades': list(TRADES), 'suburbs': suburb_facet},
    })


# ----------------------------------------------------------------------
@public_services_bp.get('/providers/<slug>')
def provider_profile(slug):
    bi_prof = BIProviderProfile.query.filter_by(slug=slug).first()
    if not bi_prof:
        return not_found('Provider not found.')
    user = db.session.get(User, bi_prof.provider_id)
    if not user or not user.is_provider or user.status != 'active':
        return not_found('Provider not found.')

    services = (ProviderService.query
                .filter_by(provider_user_id=user.id, status='active')
                .order_by(ProviderService.created_at).all())

    now = datetime.now(dt_timezone.utc)
    available, busy = free_slots(user.id, now, now + timedelta(days=14))

    card = _provider_card(user, service_count=len(services))
    card['bi_profile_id'] = str(bi_prof.id)
    card['phone'] = user.phone
    return jsonify({
        'provider': card,
        'services': [s.to_dict() for s in services],
        'availability_preview': {'available_slots': available, 'busy_slots': busy},
    })


# ----------------------------------------------------------------------
@public_services_bp.get('/providers/<slug>/availability')
def provider_availability(slug):
    """Buyer-facing AvailabilityCalendar feed — delegates to BI's resolution."""
    bi_prof = BIProviderProfile.query.filter_by(slug=slug).first()
    if not bi_prof:
        return not_found('Provider not found.')

    def _parse(v):
        try:
            dt = datetime.fromisoformat(str(v).replace('Z', '+00:00'))
            return dt.replace(tzinfo=dt_timezone.utc) if dt.tzinfo is None \
                else dt.astimezone(dt_timezone.utc)
        except (ValueError, TypeError):
            return None

    from_dt = _parse(request.args.get('from'))
    to_dt = _parse(request.args.get('to'))
    if not from_dt or not to_dt or to_dt <= from_dt \
            or to_dt - from_dt > timedelta(days=60):
        return validation_failed("Valid 'from'/'to' required (≤ 60-day window).")

    # 30-minute buyer-facing granularity — Stage 4 default #5.
    available, busy = free_slots(bi_prof.provider_id, from_dt, to_dt,
                                 granularity_minutes=30)
    return jsonify({'available_slots': available, 'booked_slots': busy})
