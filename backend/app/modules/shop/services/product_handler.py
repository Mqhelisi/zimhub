"""ProductHandler — the `listing_type='product'` handler for PurchaseInterface.

Per STAGE_2_SPEC.md §5.2.6 and PURCHASE_INTERFACE_SPEC.md §5.

KEY DESIGN POINTS:
  - One Purchase per Salesman per checkout. The cart in localStorage is split
    by Salesman; the buyer cannot mix Salesmen in a single Purchase.
  - Line items live in `purchase.domain_payload['items']`:
        [{product_id, qty, unit_price_usd_at_checkout?, name?}, ...]
    The first item's product_id is also stored as `purchase.listing_id` for
    referential symmetry; the truth lives in `domain_payload.items`.
  - Price is snapshotted INTO `domain_payload.items[i].unit_price_usd_at_checkout`
    at on_initiate. A Salesman editing a product's price afterwards does NOT
    retroactively change an in-flight Purchase.
  - `SELECT ... FOR UPDATE` on every product in the cart inside on_initiate
    prevents concurrent overselling. The loser of the race gets PurchaseHandlerError.
"""
from decimal import Decimal
from uuid import UUID as _UUID

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.modules.purchase_interface.handlers import PurchaseHandlerError
from ..models import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _coerce_uuid(v):
    if isinstance(v, _UUID):
        return v
    return _UUID(str(v))


def _items_from_payload(domain_payload, fallback_listing_id=None, fallback_qty=None):
    """Extract a normalised list of {product_id, qty} from the payload.

    Falls back to a single-item list using (listing_id, quantity) when the
    payload is empty — supports the simple single-product purchase path.
    """
    items = (domain_payload or {}).get('items')
    if items and isinstance(items, list):
        out = []
        for it in items:
            try:
                pid = _coerce_uuid(it['product_id'])
                qty = int(it.get('qty') or 1)
            except (KeyError, ValueError, TypeError):
                raise PurchaseHandlerError(
                    'invalid_payload',
                    'Each item must include a valid product_id and qty.',
                )
            if qty < 1:
                raise PurchaseHandlerError('invalid_payload', 'qty must be >= 1.')
            out.append({'product_id': pid, 'qty': qty,
                        'unit_price_usd_at_checkout': it.get('unit_price_usd_at_checkout')})
        return out
    # Fallback: single-item cart from raw args.
    if fallback_listing_id is not None and fallback_qty is not None:
        return [{'product_id': _coerce_uuid(fallback_listing_id),
                 'qty': int(fallback_qty)}]
    return []


def _resolve_label(items, salesman_user, products_by_id):
    if salesman_user and getattr(salesman_user, 'salesman_profile', None):
        shop = salesman_user.salesman_profile.shop_name
    else:
        shop = (salesman_user.name if salesman_user else 'Shop')
    total_qty = sum(it['qty'] for it in items)
    if len(items) == 1:
        p = products_by_id.get(items[0]['product_id'])
        if p:
            return f"{shop} — {p.name} × {items[0]['qty']}"
    return f"{shop} — {len(items)} items ({total_qty} units)"


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class ProductHandler:
    """Plugged into PurchaseInterface registry under listing_type='product'."""
    LISTING_TYPE = 'product'
    SELLER_CAPABILITY = 'is_salesman'

    # ------------------------------------------------------------------
    # resolve_listing — called BEFORE the Purchase row exists, to discover
    # seller/price/availability. Read-only.
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_listing(listing_id, qty=1, domain_payload=None):
        items = _items_from_payload(domain_payload, fallback_listing_id=listing_id,
                                    fallback_qty=qty)
        if not items:
            raise PurchaseHandlerError('invalid_payload', 'No items in cart.')

        product_ids = [it['product_id'] for it in items]
        products = (Product.query
                    .filter(Product.id.in_(product_ids))
                    .all())
        products_by_id = {p.id: p for p in products}

        # Validate every product exists and is active.
        for it in items:
            p = products_by_id.get(it['product_id'])
            if p is None:
                raise PurchaseHandlerError('unknown_product',
                                           f"Product {it['product_id']} not found.")
            if p.status != 'active':
                raise PurchaseHandlerError('inactive_product',
                                           f"'{p.name}' is no longer available.")

        # All items must belong to the same salesman (one Purchase per Salesman).
        salesman_ids = {p.salesman_user_id for p in products}
        if len(salesman_ids) > 1:
            raise PurchaseHandlerError(
                'salesman_mismatch',
                'All items in a single purchase must come from the same shop.',
            )
        salesman_id = next(iter(salesman_ids))

        # Availability across the cart (per item — module compares min).
        per_item_avail_qty = []
        running_total = Decimal('0')
        for it in items:
            p = products_by_id[it['product_id']]
            avail = p.available
            per_item_avail_qty.append(avail >= it['qty'])
            running_total += Decimal(str(p.price_usd)) * Decimal(it['qty'])

        cart_qty = sum(it['qty'] for it in items)
        all_available = all(per_item_avail_qty)
        # We return 'cart_qty' when available, 0 otherwise — initiate_purchase
        # compares quantity_available against quantity.
        quantity_available = cart_qty if all_available else 0

        # unit_price for the Purchase row = effective per-unit (total/cart_qty).
        unit_price = (running_total / Decimal(cart_qty)).quantize(Decimal('0.01'))

        salesman_user = products[0].salesman if products else None
        label = _resolve_label(items, salesman_user, products_by_id)

        return {
            'seller_id': salesman_id,
            'unit_price_usd': unit_price,
            'currency': 'USD',
            'quantity_available': quantity_available,
            'label': label,
        }

    # ------------------------------------------------------------------
    # on_initiate — SELECT FOR UPDATE, validate, hold, snapshot prices.
    # Called inside the same transaction as the Purchase insert.
    # ------------------------------------------------------------------
    @staticmethod
    def on_initiate(purchase, domain_payload):
        items = _items_from_payload(domain_payload, fallback_listing_id=purchase.listing_id,
                                    fallback_qty=purchase.quantity)
        if not items:
            raise PurchaseHandlerError('invalid_payload', 'No items in cart.')

        product_ids = [it['product_id'] for it in items]

        # Race-safe lock on every product in the cart.
        locked = (db.session.query(Product)
                  .filter(Product.id.in_(product_ids))
                  .with_for_update()
                  .all())
        locked_by_id = {p.id: p for p in locked}

        if len(locked) != len(set(product_ids)):
            raise PurchaseHandlerError('unknown_product',
                                       'One or more products no longer exist.')

        # Validate same salesman matches purchase.seller_id
        salesman_ids = {p.salesman_user_id for p in locked}
        if len(salesman_ids) > 1:
            raise PurchaseHandlerError(
                'salesman_mismatch',
                'All items must come from the same shop.',
            )
        if str(next(iter(salesman_ids))) != str(purchase.seller_id):
            raise PurchaseHandlerError(
                'salesman_mismatch',
                'Cart salesman does not match purchase seller.',
            )

        # Per-item: status, availability, hold, snapshot price.
        snapshotted_items = []
        for it in items:
            p = locked_by_id[it['product_id']]
            if p.status != 'active':
                raise PurchaseHandlerError(
                    'inactive_product',
                    f"'{p.name}' is no longer available.",
                )
            available = p.available
            if available < it['qty']:
                raise PurchaseHandlerError(
                    'out_of_stock',
                    f"'{p.name}' has only {available} left.",
                )
            p.stock_held = (p.stock_held or 0) + it['qty']
            snapshotted_items.append({
                'product_id': str(p.id),
                'qty': it['qty'],
                'unit_price_usd': str(p.price_usd),
                'name': p.name,
                'photo': (p.photos or [None])[0] if p.photos else None,
            })

        # Write the snapshot back into purchase.domain_payload (overwriting items).
        new_payload = dict(domain_payload or {})
        new_payload['items'] = snapshotted_items
        purchase.domain_payload = new_payload

    # ------------------------------------------------------------------
    # on_payment_confirmed — hold → sold. No new "delivery" for physical
    # goods, but the bookkeeping is the convert step.
    # ------------------------------------------------------------------
    @staticmethod
    def on_payment_confirmed(purchase, domain_payload):
        items = (domain_payload or {}).get('items') or []
        if not items:
            raise PurchaseHandlerError('invalid_payload',
                                       'Purchase has no line items.')

        product_ids = [_coerce_uuid(it['product_id']) for it in items]
        products = (db.session.query(Product)
                    .filter(Product.id.in_(product_ids))
                    .with_for_update()
                    .all())
        by_id = {str(p.id): p for p in products}

        # Convert hold → sold for each line.
        for it in items:
            p = by_id.get(str(it['product_id']))
            if p is None:
                # Product was deleted between initiate and confirm — refuse.
                raise PurchaseHandlerError(
                    'unknown_product',
                    'A product on this purchase no longer exists.',
                )
            qty = int(it['qty'])
            p.stock_held = max(0, (p.stock_held or 0) - qty)
            p.stock_sold = (p.stock_sold or 0) + qty

        return {'refs': {'fulfilled_items': len(items)}}

    # ------------------------------------------------------------------
    # on_cancel — release the hold.
    # ------------------------------------------------------------------
    @staticmethod
    def on_cancel(purchase, domain_payload):
        items = (domain_payload or {}).get('items') or []
        if not items:
            return
        product_ids = [_coerce_uuid(it['product_id']) for it in items]
        products = (db.session.query(Product)
                    .filter(Product.id.in_(product_ids))
                    .with_for_update()
                    .all())
        by_id = {str(p.id): p for p in products}
        for it in items:
            p = by_id.get(str(it['product_id']))
            if p is None:
                continue
            qty = int(it['qty'])
            p.stock_held = max(0, (p.stock_held or 0) - qty)

    # ------------------------------------------------------------------
    # on_complete — informational only; analytics hook for later.
    # ------------------------------------------------------------------
    @staticmethod
    def on_complete(purchase, domain_payload):
        return None

    # ------------------------------------------------------------------
    # on_dispute_resolution — restore stock on refunded/cancelled.
    # ------------------------------------------------------------------
    @staticmethod
    def on_dispute_resolution(purchase, resolution, domain_payload):
        if resolution == 'completed':
            return
        if resolution not in ('refunded', 'cancelled'):
            return

        items = (domain_payload or {}).get('items') or []
        if not items:
            return

        product_ids = [_coerce_uuid(it['product_id']) for it in items]
        products = (db.session.query(Product)
                    .filter(Product.id.in_(product_ids))
                    .with_for_update()
                    .all())
        by_id = {str(p.id): p for p in products}

        # Depending on prior state, stock may be 'sold' (post payment_confirmed)
        # or 'held' (pre-confirmation). Reverse whichever bucket the qty lives
        # in. We can tell from the Purchase's seller_confirmed_at: if set,
        # we previously moved hold→sold, so reverse from stock_sold;
        # otherwise reverse from stock_held.
        was_confirmed = purchase.seller_confirmed_at is not None

        for it in items:
            p = by_id.get(str(it['product_id']))
            if p is None:
                continue
            qty = int(it['qty'])
            if was_confirmed:
                p.stock_sold = max(0, (p.stock_sold or 0) - qty)
            else:
                p.stock_held = max(0, (p.stock_held or 0) - qty)
