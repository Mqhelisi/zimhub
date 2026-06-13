"""/api/admin/disputes/* — the dispute desk. Per PURCHASE_INTERFACE_SPEC.md §7.

These are super-admin only and live at /api/admin/* (not /api/super/*) to keep
the dispute desk listing-type agnostic and easy to reuse for Stage 3+ disputes
without renaming.
"""
import logging

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import error_response, not_found, forbidden, validation_failed

from ..models import PurchaseDispute
from ..services import resolve_dispute, StateError


log = logging.getLogger('zimhub.purchase_interface.disputes')

disputes_bp = Blueprint('purchase_interface_disputes', __name__, url_prefix='/api/admin')


def _require_admin(user):
    if not user.is_super_admin:
        return forbidden('You do not have access to the dispute desk.')
    return None


# ----------------------------------------------------------------------
# GET /api/admin/disputes?status=open|resolved
# ----------------------------------------------------------------------
@disputes_bp.get('/disputes')
@require_auth
def list_disputes(user):
    gate = _require_admin(user)
    if gate is not None:
        return gate

    status = (request.args.get('status') or 'open').strip().lower()
    q = PurchaseDispute.query
    if status in ('open', 'resolved'):
        q = q.filter(PurchaseDispute.status == status)
    rows = q.order_by(PurchaseDispute.created_at.desc()).limit(200).all()
    return jsonify({
        'disputes': [d.to_dict(include_purchase=True) for d in rows],
    })


# ----------------------------------------------------------------------
# GET /api/admin/disputes/:id
# ----------------------------------------------------------------------
@disputes_bp.get('/disputes/<dispute_id>')
@require_auth
def get_dispute(user, dispute_id):
    gate = _require_admin(user)
    if gate is not None:
        return gate
    d = db.session.get(PurchaseDispute, dispute_id)
    if not d:
        return not_found('Dispute not found.')
    return jsonify({'dispute': d.to_dict(include_purchase=True)})


# ----------------------------------------------------------------------
# POST /api/admin/disputes/:id/resolve
# ----------------------------------------------------------------------
@disputes_bp.post('/disputes/<dispute_id>/resolve')
@require_auth
def resolve_dispute_route(user, dispute_id):
    gate = _require_admin(user)
    if gate is not None:
        return gate

    d = db.session.get(PurchaseDispute, dispute_id)
    if not d:
        return not_found('Dispute not found.')

    data = request.get_json(silent=True) or {}
    resolution = (data.get('resolution') or '').strip().lower()
    note = (data.get('note') or '').strip() or None

    if resolution not in ('completed', 'refunded', 'cancelled'):
        return validation_failed('resolution must be completed, refunded, or cancelled.')

    try:
        resolve_dispute(dispute=d, admin=user, resolution=resolution, note=note)
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return error_response(e.code, e.message, e.http_status)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error resolving dispute')
        return error_response('server_error', 'Could not resolve dispute.', 500)

    return jsonify({'dispute': d.to_dict(include_purchase=True)})
