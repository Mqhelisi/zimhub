"""Purchase state-machine — per PURCHASE_INTERFACE_SPEC.md §4.

Public functions are the *only* way to mutate a Purchase row. Routes call into
this module; they do not write to the model directly. This keeps transitions,
audit logging, and notification fan-out in one place.

All functions assume they are inside a Flask app context with the DB session
available. They DO NOT commit — the caller is responsible for `db.session.commit()`
so a single HTTP request can be atomic.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.services import host
from app.models import User

from ..handlers import get_handler, PurchaseHandlerError
from ..models import Purchase, PurchaseEvent, PurchaseDispute


log = logging.getLogger('zimhub.purchase_interface')


class StateError(Exception):
    """Raised when a transition is illegal for the current state/role."""
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _hold_hours() -> int:
    return int(host.config('HOLD_HOURS', 24) or 24)


def _settle_hours() -> int:
    return int(host.config('SETTLE_HOURS', 72) or 72)


def _default_currency() -> str:
    return host.config('DEFAULT_CURRENCY', 'USD') or 'USD'


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _log_event(purchase: Purchase, from_status, to_status, actor_id, actor_role, note=None):
    e = PurchaseEvent(
        purchase_id=purchase.id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        actor_role=actor_role,
        note=note,
    )
    db.session.add(e)
    return e


# ---------------------------------------------------------------------------
# WhatsApp deep-link template
# ---------------------------------------------------------------------------
def build_whatsapp_link(purchase: Purchase, viewer_role: str) -> str:
    """Generate a https://wa.me link from one party to the other, prefilled.

    viewer_role ∈ {'buyer', 'seller'} — selects the recipient.
    """
    if viewer_role == 'buyer':
        counterparty = purchase.seller
    elif viewer_role == 'seller':
        counterparty = purchase.buyer
    else:
        return ''
    if counterparty is None:
        return ''

    # Pull a friendly label
    label = _purchase_label(purchase)
    total = f"${purchase.total_usd}"

    if viewer_role == 'buyer':
        text = (
            f"Hi {counterparty.name.split(' ')[0]}, this is about my ZimHub purchase: {label}. "
            f"Total {total} (qty {purchase.quantity}). "
            f"Please share your Ecocash / payment number so I can settle. "
            f"Reference: {str(purchase.id)[:8]}"
        )
    else:
        text = (
            f"Hi {counterparty.name.split(' ')[0]}, regarding your ZimHub purchase: {label}. "
            f"Total {total} (qty {purchase.quantity}). "
            f"Please pay to my Ecocash and share the confirmation code. "
            f"Reference: {str(purchase.id)[:8]}"
        )
    return host.whatsapp_link(counterparty.phone, text)


def _purchase_label(purchase: Purchase) -> str:
    """Best-effort human label for notifications and WhatsApp templates."""
    try:
        handler = get_handler(purchase.listing_type)
        info = handler.resolve_listing(
            purchase.listing_id, qty=purchase.quantity,
            domain_payload=purchase.domain_payload,
        )
        return info.get('label') or f"{purchase.listing_type} (qty {purchase.quantity})"
    except Exception:
        return f"{purchase.listing_type} (qty {purchase.quantity})"


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def _notify_initiated(purchase: Purchase):
    label = _purchase_label(purchase)
    host.notify(
        purchase.seller_id,
        'purchase_initiated',
        f"New purchase: {label}",
        f"A buyer committed to buy {label} (qty {purchase.quantity}, total ${purchase.total_usd}). "
        f"Coordinate over WhatsApp, confirm payment once received.",
        metadata={'purchase_id': str(purchase.id)},
    )
    host.notify(
        purchase.buyer_id,
        'purchase_initiated',
        f"Purchase initiated: {label}",
        f"You committed to buy {label}. Total ${purchase.total_usd}. "
        f"Open the purchase to coordinate payment over WhatsApp.",
        metadata={'purchase_id': str(purchase.id)},
    )


def _notify_payment_confirmed(purchase: Purchase):
    label = _purchase_label(purchase)
    host.notify(
        purchase.buyer_id,
        'payment_confirmed',
        f"Payment confirmed: {label}",
        f"The seller confirmed payment and delivered the goods. "
        f"Confirm receipt to finalise the purchase. "
        f"It auto-completes in about {_settle_hours()}h if you don't.",
        metadata={'purchase_id': str(purchase.id)},
    )


def _notify_completed(purchase: Purchase):
    label = _purchase_label(purchase)
    for uid in (purchase.buyer_id, purchase.seller_id):
        host.notify(
            uid,
            'purchase_completed',
            f"Purchase completed: {label}",
            f"Total ${purchase.total_usd}. Thanks for using ZimHub.",
            metadata={'purchase_id': str(purchase.id)},
        )


def _notify_cancelled(purchase: Purchase, reason: str = None):
    label = _purchase_label(purchase)
    body_suffix = f" Reason: {reason}" if reason else ''
    for uid in (purchase.buyer_id, purchase.seller_id):
        host.notify(
            uid,
            'purchase_cancelled',
            f"Purchase cancelled: {label}",
            f"This purchase was cancelled.{body_suffix}",
            metadata={'purchase_id': str(purchase.id)},
        )


def _notify_expired(purchase: Purchase):
    label = _purchase_label(purchase)
    for uid in (purchase.buyer_id, purchase.seller_id):
        host.notify(
            uid,
            'purchase_expired',
            f"Purchase expired: {label}",
            f"The payment hold for this purchase expired. The reservation was released.",
            metadata={'purchase_id': str(purchase.id)},
        )


def _notify_dispute_raised(purchase: Purchase, dispute: PurchaseDispute):
    label = _purchase_label(purchase)
    counterparty_id = purchase.seller_id if dispute.raised_by_role == 'buyer' else purchase.buyer_id
    host.notify(
        counterparty_id,
        'purchase_disputed',
        f"Dispute raised: {label}",
        f"The {dispute.raised_by_role} raised a dispute. Reason: {dispute.reason}. "
        f"A ZimHub admin will review.",
        metadata={'purchase_id': str(purchase.id), 'dispute_id': str(dispute.id)},
    )
    # Notify every super admin (dispute desk).
    admins = User.query.filter_by(is_super_admin=True).all()
    for a in admins:
        host.notify(
            a.id,
            'purchase_disputed',
            f"Dispute opened: {label}",
            f"The {dispute.raised_by_role} disputed a purchase. Open the dispute desk to review.",
            metadata={'purchase_id': str(purchase.id), 'dispute_id': str(dispute.id)},
        )


def _notify_dispute_resolved(purchase: Purchase, dispute: PurchaseDispute):
    label = _purchase_label(purchase)
    note = dispute.resolution_note or ''
    suffix = '. Refunds are processed manually — please coordinate via WhatsApp.' if dispute.resolution == 'refunded' else ''
    for uid in (purchase.buyer_id, purchase.seller_id):
        host.notify(
            uid,
            'dispute_resolved',
            f"Dispute resolved: {label}",
            f"Resolution: {dispute.resolution}. {note}{suffix}".strip(),
            metadata={'purchase_id': str(purchase.id), 'dispute_id': str(dispute.id)},
        )


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------
def initiate_purchase(*, buyer, listing_type: str, listing_id, quantity: int,
                      domain_payload: dict = None) -> Purchase:
    """Create a new Purchase in awaiting_payment, place the hold via the handler.

    Raises StateError or PurchaseHandlerError on failure; in those cases NO
    Purchase row is created.
    """
    if quantity is None or int(quantity) < 1:
        raise StateError('validation_failed', 'Quantity must be >= 1.')
    quantity = int(quantity)

    handler = get_handler(listing_type)
    info = handler.resolve_listing(listing_id, qty=quantity, domain_payload=domain_payload)
    if not info:
        raise PurchaseHandlerError('unknown_listing', 'Listing could not be resolved.')

    seller_id = info['seller_id']
    if str(seller_id) == str(buyer.id):
        raise StateError('forbidden', 'You cannot buy from yourself.', http_status=403)

    if int(info.get('quantity_available', 0) or 0) < quantity:
        raise PurchaseHandlerError('sold_out', info.get('label', listing_type) + ' is unavailable.')

    unit_price = Decimal(str(info['unit_price_usd']))
    total = (unit_price * Decimal(quantity)).quantize(Decimal('0.01'))

    purchase = Purchase(
        listing_type=listing_type,
        listing_id=listing_id,
        seller_id=seller_id,
        buyer_id=buyer.id,
        quantity=quantity,
        unit_price_usd=unit_price,
        total_usd=total,
        currency=info.get('currency') or _default_currency(),
        status='awaiting_payment',
        domain_payload=domain_payload or {},
        hold_expires_at=_now() + timedelta(hours=_hold_hours()),
    )
    db.session.add(purchase)
    db.session.flush()  # need purchase.id for events / handler

    # Handler places the hold. May raise PurchaseHandlerError; row is rolled back.
    try:
        handler.on_initiate(purchase, purchase.domain_payload or {})
    except PurchaseHandlerError:
        db.session.rollback()
        raise

    _log_event(purchase, None, 'awaiting_payment', buyer.id, 'buyer', note='Purchase initiated.')
    _notify_initiated(purchase)
    return purchase


def confirm_payment(*, purchase: Purchase, user, payment_ref: str = None) -> Purchase:
    """Seller marks payment received → fulfillment fires → awaiting_buyer_confirmation."""
    if str(user.id) != str(purchase.seller_id):
        raise StateError('forbidden', 'Only the seller can confirm payment.', http_status=403)

    if purchase.status == 'awaiting_buyer_confirmation':
        # Idempotent — already done.
        if payment_ref and not purchase.payment_ref:
            purchase.payment_ref = payment_ref[:120]
        return purchase
    if purchase.status != 'awaiting_payment':
        raise StateError('invalid_state',
                         f"Cannot confirm payment from status={purchase.status}.")

    handler = get_handler(purchase.listing_type)
    # Fulfillment fires. If it fails (sold out mid-flight), reject and keep hold.
    result = handler.on_payment_confirmed(purchase, purchase.domain_payload or {})

    if payment_ref:
        purchase.payment_ref = payment_ref[:120]
    if isinstance(result, dict) and 'refs' in result:
        purchase.fulfillment_refs = result['refs']
    elif isinstance(result, dict):
        purchase.fulfillment_refs = result

    prev = purchase.status
    purchase.seller_confirmed_at = _now()
    purchase.auto_complete_at = _now() + timedelta(hours=_settle_hours())
    purchase.status = 'awaiting_buyer_confirmation'

    _log_event(purchase, prev, 'awaiting_buyer_confirmation', user.id, 'seller',
               note='Payment confirmed; goods delivered.')
    _notify_payment_confirmed(purchase)
    return purchase


def confirm_receipt(*, purchase: Purchase, user) -> Purchase:
    """Buyer marks goods received → completed."""
    if str(user.id) != str(purchase.buyer_id):
        raise StateError('forbidden', 'Only the buyer can confirm receipt.', http_status=403)
    if purchase.status == 'completed':
        return purchase
    if purchase.status != 'awaiting_buyer_confirmation':
        raise StateError('invalid_state',
                         f"Cannot confirm receipt from status={purchase.status}.")

    prev = purchase.status
    purchase.buyer_confirmed_at = _now()
    purchase.completed_at = _now()
    purchase.status = 'completed'

    handler = get_handler(purchase.listing_type)
    try:
        if hasattr(handler, 'on_complete'):
            handler.on_complete(purchase, purchase.domain_payload or {})
    except Exception as e:
        # on_complete is informational; don't block transition.
        log.warning('on_complete handler raised for purchase=%s: %s', purchase.id, e)

    _log_event(purchase, prev, 'completed', user.id, 'buyer', note='Receipt confirmed.')
    _notify_completed(purchase)
    return purchase


def cancel_purchase(*, purchase: Purchase, user, reason: str = None) -> Purchase:
    """Buyer pre-payment OR seller while unpaid may cancel."""
    is_buyer = str(user.id) == str(purchase.buyer_id)
    is_seller = str(user.id) == str(purchase.seller_id)
    if not (is_buyer or is_seller):
        raise StateError('forbidden', 'Only a party to this purchase can cancel it.', http_status=403)

    if purchase.status == 'cancelled':
        return purchase
    if purchase.status != 'awaiting_payment':
        raise StateError('invalid_state',
                         f"Cannot cancel from status={purchase.status}.")

    handler = get_handler(purchase.listing_type)
    try:
        handler.on_cancel(purchase, purchase.domain_payload or {})
    except Exception as e:
        log.warning('on_cancel handler raised for purchase=%s: %s', purchase.id, e)

    prev = purchase.status
    purchase.status = 'cancelled'
    role = 'buyer' if is_buyer else 'seller'
    _log_event(purchase, prev, 'cancelled', user.id, role, note=reason)
    _notify_cancelled(purchase, reason)
    return purchase


def raise_dispute(*, purchase: Purchase, user, reason: str) -> PurchaseDispute:
    """Either party escalates → status = disputed; freezes auto-complete."""
    is_buyer = str(user.id) == str(purchase.buyer_id)
    is_seller = str(user.id) == str(purchase.seller_id)
    if not (is_buyer or is_seller):
        raise StateError('forbidden', 'Only a party to this purchase can dispute it.', http_status=403)
    if purchase.status not in ('awaiting_payment', 'awaiting_buyer_confirmation'):
        raise StateError('invalid_state',
                         f"Cannot dispute from status={purchase.status}.")
    if not reason or not reason.strip():
        raise StateError('validation_failed', 'A dispute reason is required.')

    if purchase.has_open_dispute():
        raise StateError('conflict', 'A dispute is already open.', http_status=409)

    role = 'buyer' if is_buyer else 'seller'
    dispute = PurchaseDispute(
        purchase_id=purchase.id,
        raised_by=user.id,
        raised_by_role=role,
        reason=reason.strip(),
        status='open',
    )
    db.session.add(dispute)
    db.session.flush()

    prev = purchase.status
    purchase.dispute_id = dispute.id
    purchase.status = 'disputed'
    # auto-complete is frozen — clear the timer so the sweeper ignores this row.
    purchase.auto_complete_at = None

    _log_event(purchase, prev, 'disputed', user.id, role, note=f'Dispute raised: {reason[:160]}')
    _notify_dispute_raised(purchase, dispute)
    return dispute


def resolve_dispute(*, dispute: PurchaseDispute, admin, resolution: str, note: str = None) -> PurchaseDispute:
    """Admin resolves a dispute → completed | refunded | cancelled."""
    if not getattr(admin, 'is_super_admin', False) and not host.is_dispute_admin(admin):
        raise StateError('forbidden', 'Only an admin can resolve disputes.', http_status=403)
    if dispute.status == 'resolved':
        return dispute
    if resolution not in ('completed', 'refunded', 'cancelled'):
        raise StateError('validation_failed',
                         'Resolution must be one of completed, refunded, cancelled.')

    purchase = dispute.purchase
    prev_status = purchase.status

    # Fire handler resolution. May restore stock for refunded/cancelled.
    handler = get_handler(purchase.listing_type)
    try:
        if hasattr(handler, 'on_dispute_resolution'):
            handler.on_dispute_resolution(purchase, resolution, purchase.domain_payload or {})
    except Exception as e:
        log.warning('on_dispute_resolution handler raised for purchase=%s: %s', purchase.id, e)

    purchase.status = resolution
    if resolution == 'completed':
        if not purchase.completed_at:
            purchase.completed_at = _now()

    dispute.status = 'resolved'
    dispute.resolution = resolution
    dispute.resolution_note = (note or '').strip() or None
    dispute.resolved_by = admin.id
    dispute.resolved_at = _now()

    _log_event(purchase, prev_status, resolution, admin.id, 'admin',
               note=f'Dispute resolved as {resolution}.' + (f' {note}' if note else ''))
    _notify_dispute_resolved(purchase, dispute)
    return dispute


# ---------------------------------------------------------------------------
# Sweepers (called by APScheduler in app/jobs/scheduler.py)
# ---------------------------------------------------------------------------
def expire_purchases_due() -> int:
    """Find awaiting_payment Purchases past hold_expires_at and expire them.

    Returns the number expired. Each transition commits independently so a
    single failure doesn't block the rest.
    """
    now = _now()
    rows = (Purchase.query
            .filter(Purchase.status == 'awaiting_payment')
            .filter(Purchase.hold_expires_at != None)  # noqa: E711
            .filter(Purchase.hold_expires_at < now)
            .all())

    count = 0
    for p in rows:
        try:
            handler = get_handler(p.listing_type)
            try:
                handler.on_cancel(p, p.domain_payload or {})
            except Exception as he:
                log.warning('on_cancel handler raised during expire for purchase=%s: %s', p.id, he)
            prev = p.status
            p.status = 'expired'
            _log_event(p, prev, 'expired', None, 'system', note='Hold window elapsed.')
            _notify_expired(p)
            db.session.commit()
            count += 1
        except SQLAlchemyError:
            db.session.rollback()
            log.exception('Failed to expire purchase=%s', p.id)
        except Exception:
            db.session.rollback()
            log.exception('Unexpected error expiring purchase=%s', p.id)
    return count


def auto_complete_purchases_due() -> int:
    """Find awaiting_buyer_confirmation Purchases past auto_complete_at and complete them.

    Skips any with an open dispute (auto_complete_at is cleared on dispute, but
    we defensively re-check).
    """
    now = _now()
    rows = (Purchase.query
            .filter(Purchase.status == 'awaiting_buyer_confirmation')
            .filter(Purchase.auto_complete_at != None)  # noqa: E711
            .filter(Purchase.auto_complete_at < now)
            .all())

    count = 0
    for p in rows:
        if p.has_open_dispute():
            continue
        try:
            handler = get_handler(p.listing_type)
            try:
                if hasattr(handler, 'on_complete'):
                    handler.on_complete(p, p.domain_payload or {})
            except Exception as he:
                log.warning('on_complete handler raised during auto-complete for purchase=%s: %s', p.id, he)
            prev = p.status
            p.status = 'completed'
            p.completed_at = _now()
            _log_event(p, prev, 'completed', None, 'system',
                       note='Auto-completed after settle window.')
            _notify_completed(p)
            db.session.commit()
            count += 1
        except SQLAlchemyError:
            db.session.rollback()
            log.exception('Failed to auto-complete purchase=%s', p.id)
        except Exception:
            db.session.rollback()
            log.exception('Unexpected error auto-completing purchase=%s', p.id)
    return count
