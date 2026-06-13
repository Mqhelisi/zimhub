"""BookingInterface dispute desk — BI spec §8 (admin, optional).

    GET  /api/admin/booking-disputes?status=        (default open)
    GET  /api/admin/booking-disputes/:id
    POST /api/admin/booking-disputes/:id/resolve    {resolution, note?}

SEPARATE from PurchaseInterface's /api/admin/disputes — independent systems,
independent desks (Stage 4 handoff hard rule).
"""
import logging

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_role
from app.utils.errors import error_response, not_found, validation_failed

from ..models import BookingDispute
from ..services import resolve_dispute, booking_label, BookingStateError


log = logging.getLogger('zimhub.booking_interface.disputes')

booking_disputes_bp = Blueprint('booking_interface_disputes', __name__,
                                url_prefix='/api/admin')


@booking_disputes_bp.get('/booking-disputes')
@require_role('super_admin')
def list_booking_disputes(user):
    status = (request.args.get('status') or 'open').strip()
    q = BookingDispute.query
    if status != 'all':
        q = q.filter(BookingDispute.status == status)
    rows = q.order_by(BookingDispute.created_at.desc()).all()
    out = []
    for d in rows:
        item = d.to_dict(include_booking=True)
        if d.booking:
            item['booking']['label'] = booking_label(d.booking)
        out.append(item)
    return jsonify({'disputes': out})


@booking_disputes_bp.get('/booking-disputes/<uuid:dispute_id>')
@require_role('super_admin')
def get_booking_dispute(user, dispute_id):
    d = db.session.get(BookingDispute, dispute_id)
    if not d:
        return not_found('Dispute not found.')
    item = d.to_dict(include_booking=True)
    if d.booking:
        item['booking'] = d.booking.to_dict(viewer=user, include_events=True,
                                            label=booking_label(d.booking))
    return jsonify({'dispute': item})


@booking_disputes_bp.post('/booking-disputes/<uuid:dispute_id>/resolve')
@require_role('super_admin')
def resolve_booking_dispute(user, dispute_id):
    d = db.session.get(BookingDispute, dispute_id)
    if not d:
        return not_found('Dispute not found.')
    data = request.get_json(silent=True) or {}
    resolution = (data.get('resolution') or '').strip()
    if resolution not in ('completed', 'cancelled'):
        return validation_failed("resolution must be 'completed' or 'cancelled'.")
    try:
        resolve_dispute(dispute=d, admin=user, resolution=resolution,
                        note=(data.get('note') or '').strip() or None)
        db.session.commit()
    except BookingStateError as e:
        db.session.rollback()
        return error_response(e.code, e.message, e.http_status)
    return jsonify({'dispute': d.to_dict(include_booking=True)})
