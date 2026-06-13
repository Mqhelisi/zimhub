"""/api/purchases/* routes — per PURCHASE_INTERFACE_SPEC.md §7."""
import logging

from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response, validation_failed, not_found, forbidden, conflict,
)

from ..handlers import PurchaseHandlerError
from ..models import Purchase
from ..services import (
    initiate_purchase, confirm_payment, confirm_receipt,
    cancel_purchase, raise_dispute, build_whatsapp_link, StateError,
)


log = logging.getLogger('zimhub.purchase_interface.routes')

purchases_bp = Blueprint('purchase_interface_purchases', __name__, url_prefix='/api')


def _err_from_state(e: StateError):
    return error_response(e.code, e.message, e.http_status)


def _err_from_handler(e: PurchaseHandlerError):
    return error_response(e.code, e.message, e.http_status)


def _load_purchase_or_404(purchase_id):
    p = db.session.get(Purchase, purchase_id)
    if not p:
        return None
    return p


def _viewer_can_see(purchase: Purchase, user) -> bool:
    if user is None:
        return False
    if str(user.id) == str(purchase.buyer_id):
        return True
    if str(user.id) == str(purchase.seller_id):
        return True
    if getattr(user, 'is_super_admin', False):
        return True
    return False


# ----------------------------------------------------------------------
# POST /api/purchases  — initiate
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases')
@require_auth
def create_purchase(user):
    data = request.get_json(silent=True) or {}
    listing_type = (data.get('listing_type') or '').strip()
    listing_id = data.get('listing_id')
    quantity = data.get('quantity')
    domain_payload = data.get('domain_payload') or {}

    if not listing_type or not listing_id:
        return validation_failed('listing_type and listing_id are required.')
    if not quantity or int(quantity) < 1:
        return validation_failed('quantity must be a positive integer.')

    try:
        purchase = initiate_purchase(
            buyer=user,
            listing_type=listing_type,
            listing_id=listing_id,
            quantity=int(quantity),
            domain_payload=domain_payload,
        )
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return _err_from_state(e)
    except PurchaseHandlerError as e:
        db.session.rollback()
        return _err_from_handler(e)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error creating purchase')
        return error_response('server_error', 'Could not create purchase.', 500)

    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)}), 201


# ----------------------------------------------------------------------
# GET /api/purchases/:id  — detail
# ----------------------------------------------------------------------
@purchases_bp.get('/purchases/<purchase_id>')
@require_auth
def get_purchase(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')
    if not _viewer_can_see(purchase, user):
        return forbidden('You do not have access to this purchase.')
    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)})


# ----------------------------------------------------------------------
# GET /api/my/purchases?role=buyer|seller&status=...
# ----------------------------------------------------------------------
@purchases_bp.get('/my/purchases')
@require_auth
def list_my_purchases(user):
    role = (request.args.get('role') or 'buyer').strip().lower()
    status = (request.args.get('status') or '').strip().lower()
    listing_type = (request.args.get('listing_type') or '').strip()

    q = Purchase.query
    if role == 'buyer':
        q = q.filter(Purchase.buyer_id == user.id)
    elif role == 'seller':
        q = q.filter(Purchase.seller_id == user.id)
    else:
        return validation_failed('role must be "buyer" or "seller".')
    if status:
        q = q.filter(Purchase.status == status)
    if listing_type:
        q = q.filter(Purchase.listing_type == listing_type)

    rows = q.order_by(Purchase.created_at.desc()).limit(200).all()
    return jsonify({'purchases': [r.to_dict(viewer=user) for r in rows]})


# ----------------------------------------------------------------------
# POST /api/purchases/:id/whatsapp
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases/<purchase_id>/whatsapp')
@require_auth
def whatsapp_link_for_purchase(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')
    if not _viewer_can_see(purchase, user):
        return forbidden('You do not have access to this purchase.')

    if str(user.id) == str(purchase.buyer_id):
        role = 'buyer'
    elif str(user.id) == str(purchase.seller_id):
        role = 'seller'
    else:
        # Admins viewing can still see a link from the buyer's POV.
        role = 'buyer'

    url = build_whatsapp_link(purchase, role)
    return jsonify({'url': url})


# ----------------------------------------------------------------------
# POST /api/purchases/:id/confirm-payment  — seller
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases/<purchase_id>/confirm-payment')
@require_auth
def confirm_payment_route(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')

    data = request.get_json(silent=True) or {}
    payment_ref = (data.get('payment_ref') or '').strip() or None

    try:
        confirm_payment(purchase=purchase, user=user, payment_ref=payment_ref)
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return _err_from_state(e)
    except PurchaseHandlerError as e:
        db.session.rollback()
        return _err_from_handler(e)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error confirming payment')
        return error_response('server_error', 'Could not confirm payment.', 500)

    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)})


# ----------------------------------------------------------------------
# POST /api/purchases/:id/confirm-receipt  — buyer
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases/<purchase_id>/confirm-receipt')
@require_auth
def confirm_receipt_route(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')

    try:
        confirm_receipt(purchase=purchase, user=user)
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return _err_from_state(e)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error confirming receipt')
        return error_response('server_error', 'Could not confirm receipt.', 500)

    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)})


# ----------------------------------------------------------------------
# POST /api/purchases/:id/cancel  — buyer pre-payment OR seller while unpaid
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases/<purchase_id>/cancel')
@require_auth
def cancel_route(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')

    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip() or None

    try:
        cancel_purchase(purchase=purchase, user=user, reason=reason)
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return _err_from_state(e)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error cancelling purchase')
        return error_response('server_error', 'Could not cancel.', 500)

    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)})


# ----------------------------------------------------------------------
# POST /api/purchases/:id/dispute  — either party
# ----------------------------------------------------------------------
@purchases_bp.post('/purchases/<purchase_id>/dispute')
@require_auth
def dispute_route(user, purchase_id):
    purchase = _load_purchase_or_404(purchase_id)
    if not purchase:
        return not_found('Purchase not found.')

    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip()
    if not reason:
        return validation_failed('reason is required.')

    try:
        raise_dispute(purchase=purchase, user=user, reason=reason)
        db.session.commit()
    except StateError as e:
        db.session.rollback()
        return _err_from_state(e)
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('DB error raising dispute')
        return error_response('server_error', 'Could not raise dispute.', 500)

    return jsonify({'purchase': purchase.to_dict(viewer=user, include_events=True)})
