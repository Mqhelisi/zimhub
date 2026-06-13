"""BookingInterface — reusable time-booking module. See docs/BOOKING_INTERFACE_SPEC.md.

Sibling of PurchaseInterface; same module shape and host seams, but settled by
MUTUAL AGREEMENT instead of payment + delivery. Separate tables, separate
state machine, separate handler registry, separate dispute desk. Never moves
money.
"""
from .handlers import (  # noqa: F401
    register_bookable, get_bookable_handler, BookingHandlerError,
    BOOKABLE_HANDLERS, DefaultProviderHandler,
)
