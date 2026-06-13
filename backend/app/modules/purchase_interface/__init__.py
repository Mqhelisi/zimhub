"""PurchaseInterface — the reusable purchase/settlement module.

This module is design-agnostic on purpose. It owns:
  - the Purchase/PurchaseEvent/PurchaseDispute tables
  - the state machine
  - /api/purchases/* and /api/admin/disputes endpoints
  - background sweepers (hold expiry + auto-complete)
  - the handler registry (`register_purchasable`)

It does NOT own user accounts or sellable catalogs — domain modules (Shop,
TicketGenerator, …) register handlers and own their own listings.

See `docs/PURCHASE_INTERFACE_SPEC.md` for the full contract.
"""
from .handlers import (
    register_purchasable,
    get_handler,
    PurchaseHandlerError,
    HANDLERS,
)

__all__ = [
    'register_purchasable',
    'get_handler',
    'PurchaseHandlerError',
    'HANDLERS',
]
