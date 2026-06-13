"""BookingInterface routes — BOOKING_INTERFACE_SPEC.md §8.

Public / requester:
    GET  /api/providers/:id                      — public profile + rate
    GET  /api/providers/:id/availability         — free slots; opaque busy
    POST /api/bookings                           — → requested
    GET  /api/bookings/:id                       — party/admin; permitted actions
    GET  /api/my/bookings?role=&status=          — caller's bookings in role
    POST /api/bookings/:id/whatsapp              — {url} deep-link
    POST /api/bookings/:id/accept|decline|cancel|no-show|dispute
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response, validation_failed, not_found, forbidden,
)
from app.services import host

from ..models import Booking, BIProviderProfile
from ..handlers import BookingHandlerError
from ..services import (
    request_booking, accept_booking, decline_booking, cancel_booking,
    mark_no_show, mark_complete, raise_dispute, build_whatsapp_link,
    booking_label, free_slots, BookingStateError,
)


log = logging.getLogger('zimhub.booking_interface.routes')

bookings_bp = Blueprint('booking_interface_bookings', __name__, url_prefix='/api')


def _err_state(e: BookingStateError):
    return error_response(e.code, e.message, e.http_status)


def _err_handler(e: BookingHandlerError):
    return error_response(e.code, e.message, e.http_status)


def _parse_dt(value, field):
    if not value:
        raise BookingStateError('validation_failed', f'{field} is required.', 400)
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        raise BookingStateError('validation_failed', f'{field} is not a valid ISO datetime.', 400)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _viewer_can_see(booking, user) -> bool:
    if user is None:
        return False
    return (str(user.id) in (str(booking.requester_id), str(booking.provider_id))
            or bool(getattr(user, 'is_super_admin', False)))


# ----------------------------------------------------------------------
# Public provider endpoints
# ----------------------------------------------------------------------
@bookings_bp.get('/providers/<uuid:profile_id>')
def public_provider_profile(profile_id):
    prof = db.session.get(BIProviderProfile, profile_id)
    if not prof:
        return not_found('Provider not found.')
    return jsonify({'provider': prof.to_dict()})


@bookings_bp.get('/providers/<uuid:profile_id>/availability')
def public_provider_availability(profile_id):
    """Free slots only; confirmed bookings shown as opaque 'busy' (§8)."""
    prof = db.session.get(BIProviderProfile, profile_id)
    if not prof:
        return not_found('Provider not found.')
    try:
        from_dt = _parse_dt(request.args.get('from'), 'from')
        to_dt = _parse_dt(request.args.get('to'), 'to')
    except BookingStateError as e:
        return _err_state(e)
    if to_dt <= from_dt or to_dt - from_dt > timedelta(days=60):
        return validation_failed('Window must be positive and at most 60 days.')
    available, busy = free_slots(prof.provider_id, from_dt, to_dt)
    return jsonify({'available_slots': available, 'busy_slots': busy})


# ----------------------------------------------------------------------
# POST /api/bookings — → requested
# ----------------------------------------------------------------------
@bookings_bp.post('/bookings')
@require_auth
def create_booking(user):
    data = request.get_json(silent=True) or {}
    bookable_type = (data.get('bookable_type') or 'service_provider').strip()
    bookable_id = data.get('bookable_id')
    if not bookable_id:
        return validation_failed('bookable_id is required.')
    try:
        start_at = _parse_dt(data.get('start_at'), 'start_at')
        end_at = _parse_dt(data.get('end_at'), 'end_at')
        booking = request_booking(
            requester=user,
            bookable_type=bookable_type,
            bookable_id=bookable_id,
            start_at=start_at, end_at=end_at,
            message=(data.get('message') or '').strip() or None,
            domain_payload=data.get('domain_payload') or {},
        )
        db.session.commit()
    except BookingStateError as e:
        db.session.rollback()
        return _err_state(e)
    except BookingHandlerError as e:
        db.session.rollback()
        return _err_handler(e)
    return jsonify({'booking': booking.to_dict(viewer=user, label=booking_label(booking))}), 201


# ----------------------------------------------------------------------
# GET /api/bookings/:id
# ----------------------------------------------------------------------
@bookings_bp.get('/bookings/<uuid:booking_id>')
@require_auth
def get_booking(user, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return not_found('Booking not found.')
    if not _viewer_can_see(booking, user):
        return forbidden()
    return jsonify({'booking': booking.to_dict(
        viewer=user, include_events=True, label=booking_label(booking))})


# ----------------------------------------------------------------------
# GET /api/my/bookings?role=requester|provider&status=
# ----------------------------------------------------------------------
@bookings_bp.get('/my/bookings')
@require_auth
def my_bookings(user):
    role = (request.args.get('role') or 'requester').strip()
    status = (request.args.get('status') or '').strip()
    if role == 'provider':
        q = Booking.query.filter(Booking.provider_id == user.id)
    else:
        role = 'requester'
        q = Booking.query.filter(Booking.requester_id == user.id)
    if status:
        q = q.filter(Booking.status == status)
    rows = q.order_by(Booking.start_at.desc()).all()
    return jsonify({'bookings': [
        b.to_dict(viewer=user, label=booking_label(b)) for b in rows
    ], 'role': role})


# ----------------------------------------------------------------------
# POST /api/bookings/:id/whatsapp — {url}
# ----------------------------------------------------------------------
@bookings_bp.post('/bookings/<uuid:booking_id>/whatsapp')
@require_auth
def booking_whatsapp(user, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return not_found('Booking not found.')
    if str(user.id) == str(booking.requester_id):
        role = 'requester'
    elif str(user.id) == str(booking.provider_id):
        role = 'provider'
    else:
        return forbidden()
    return jsonify({'url': build_whatsapp_link(booking, role)})


# ----------------------------------------------------------------------
# Transition actions
# ----------------------------------------------------------------------
def _transition(viewer, booking_id, fn, **kwargs):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return not_found('Booking not found.')
    try:
        fn(booking=booking, **kwargs)
        db.session.commit()
    except BookingStateError as e:
        db.session.rollback()
        return _err_state(e)
    except BookingHandlerError as e:
        db.session.rollback()
        return _err_handler(e)
    db.session.refresh(booking)
    return jsonify({'booking': booking.to_dict(
        viewer=viewer, include_events=True, label=booking_label(booking))})


@bookings_bp.post('/bookings/<uuid:booking_id>/accept')
@require_auth
def accept(user, booking_id):
    return _transition(user, booking_id, accept_booking, provider=user)


@bookings_bp.post('/bookings/<uuid:booking_id>/decline')
@require_auth
def decline(user, booking_id):
    data = request.get_json(silent=True) or {}
    return _transition(user, booking_id, decline_booking, provider=user,
                       reason=(data.get('reason') or '').strip() or None)


@bookings_bp.post('/bookings/<uuid:booking_id>/cancel')
@require_auth
def cancel(user, booking_id):
    data = request.get_json(silent=True) or {}
    return _transition(user, booking_id, cancel_booking, user=user,
                       reason=(data.get('reason') or '').strip() or None)


@bookings_bp.post('/bookings/<uuid:booking_id>/no-show')
@require_auth
def no_show(user, booking_id):
    return _transition(user, booking_id, mark_no_show, provider=user)


@bookings_bp.post('/bookings/<uuid:booking_id>/complete')
@require_auth
def complete(user, booking_id):
    """Provider's manual 'Mark complete' (Stage 4 §11.8); the sweeper is the
    automatic path. Backend rejects early completion."""
    return _transition(user, booking_id, mark_complete, provider=user)


@bookings_bp.post('/bookings/<uuid:booking_id>/dispute')
@require_auth
def dispute(user, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return not_found('Booking not found.')
    data = request.get_json(silent=True) or {}
    try:
        d = raise_dispute(booking=booking, user=user,
                          reason=(data.get('reason') or '').strip())
        db.session.commit()
    except BookingStateError as e:
        db.session.rollback()
        return _err_state(e)
    db.session.refresh(booking)
    return jsonify({
        'dispute': d.to_dict(),
        'booking': booking.to_dict(viewer=user, include_events=True,
                                   label=booking_label(booking)),
    }), 201
