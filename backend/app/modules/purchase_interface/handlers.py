"""Pluggable handler registry. Per PURCHASE_INTERFACE_SPEC.md §5.

A domain module wanting to sell through PurchaseInterface registers a class
that implements the handler protocol:

    handler.resolve_listing(listing_id, qty=1, domain_payload=None) -> {
        seller_id, unit_price_usd, currency, quantity_available, label
    }
    handler.on_initiate(purchase, domain_payload)
    handler.on_payment_confirmed(purchase, domain_payload) -> {refs:[...]} | raises
    handler.on_cancel(purchase, domain_payload)
    handler.on_complete(purchase, domain_payload)               # optional / no-op default
    handler.on_dispute_resolution(purchase, resolution, domain_payload)

Handlers are looked up by `purchase.listing_type` string.
"""
from typing import Type, Dict


class PurchaseHandlerError(Exception):
    """Raised by a handler to abort a transition with a machine code.

    Examples:
        raise PurchaseHandlerError('sold_out', 'Phone XYZ is sold out.')
        raise PurchaseHandlerError('inactive_product', 'Product is archived.')

    The route layer translates this into a 409 JSON response.
    """
    def __init__(self, code: str, message: str = None, http_status: int = 409):
        self.code = code
        self.message = message or code
        self.http_status = http_status
        super().__init__(self.message)


# listing_type -> handler class
HANDLERS: Dict[str, Type] = {}


def register_purchasable(listing_type: str, handler_cls: Type) -> None:
    """Register a domain handler. Idempotent — re-registering the same class is a no-op.

    Called from `app/modules/<domain>/__init__.py` or `services/<domain>_handler.py`
    at app boot, after blueprints are registered.
    """
    if not listing_type:
        raise ValueError('listing_type is required')
    if not handler_cls:
        raise ValueError('handler_cls is required')
    existing = HANDLERS.get(listing_type)
    if existing is handler_cls:
        return
    HANDLERS[listing_type] = handler_cls


def get_handler(listing_type: str):
    """Return the registered handler class for a listing_type, or raise."""
    h = HANDLERS.get(listing_type)
    if h is None:
        raise PurchaseHandlerError(
            'unknown_listing_type',
            f"No handler registered for listing_type={listing_type!r}.",
            http_status=400,
        )
    return h
