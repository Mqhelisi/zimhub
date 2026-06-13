"""BookingInterface pluggable bookable-handler registry — BI spec §5.

A SEPARATE registry from PurchaseInterface's. The two systems never share
state. A domain wanting bookable things registers a class implementing:

    handler.resolve_bookable(bookable_id, domain_payload=None) -> {
        provider_id, timezone, hourly_rate_usd?, min_hours?, max_hours?, label, ...
    }
    handler.is_open(bookable_id, start_at, end_at) -> bool
    handler.on_request(booking, domain_payload)        # optional side-effects
    handler.on_confirm(booking, domain_payload)
    handler.on_decline(booking, domain_payload)        # optional
    handler.on_cancel(booking, domain_payload)
    handler.on_complete(booking, domain_payload)
    handler.on_no_show(booking, domain_payload)        # optional
    handler.on_dispute_resolution(booking, resolution, domain_payload)  # optional

Handlers are looked up by `booking.bookable_type` string. If a domain
registers no handler, the built-in DefaultProviderHandler books the
provider's own time directly (BI spec §5 "service_provider behaviour").
"""
from typing import Type, Dict


class BookingHandlerError(Exception):
    """Raised by a handler to abort a transition with a machine code.

    The route layer translates this into a JSON error response.
    """
    def __init__(self, code: str, message: str = None, http_status: int = 409):
        self.code = code
        self.message = message or code
        self.http_status = http_status
        super().__init__(self.message)


# bookable_type -> handler class. INDEPENDENT of PurchaseInterface.HANDLERS.
BOOKABLE_HANDLERS: Dict[str, Type] = {}


def register_bookable(bookable_type: str, handler_cls: Type) -> None:
    """Register a domain handler. Idempotent for the same class; a later
    registration with a different class replaces the earlier one (this is how
    Stage 4's ServiceHandler supersedes the built-in default for
    'service_provider')."""
    if not bookable_type:
        raise ValueError('bookable_type is required')
    if not handler_cls:
        raise ValueError('handler_cls is required')
    if BOOKABLE_HANDLERS.get(bookable_type) is handler_cls:
        return
    BOOKABLE_HANDLERS[bookable_type] = handler_cls


def get_bookable_handler(bookable_type: str):
    h = BOOKABLE_HANDLERS.get(bookable_type)
    if h is None:
        raise BookingHandlerError(
            'unknown_bookable_type',
            f"No handler registered for bookable_type={bookable_type!r}.",
            http_status=400,
        )
    return h


class DefaultProviderHandler:
    """Built-in behaviour: the bookable IS the provider's BI profile row.

    Registered under 'service_provider' at module import; Stage 4's
    services_section replaces it with ServiceHandler (bookable = catalog
    service) when it registers at app boot.
    """
    BOOKABLE_TYPE = 'service_provider'

    @staticmethod
    def resolve_bookable(bookable_id, domain_payload=None):
        from .models import BIProviderProfile
        prof = BIProviderProfile.query.get(bookable_id)
        if not prof:
            raise BookingHandlerError('unknown_bookable', 'No such provider profile.', 404)
        return {
            'provider_id': prof.provider_id,
            'timezone': prof.timezone or 'Africa/Harare',
            'hourly_rate_usd': prof.hourly_rate_usd,
            'min_hours': prof.min_hours,
            'max_hours': prof.max_hours,
            'label': prof.display_name,
        }

    @staticmethod
    def is_open(bookable_id, start_at, end_at):
        from .models import BIProviderProfile
        from .services.availability import range_is_bookable
        prof = BIProviderProfile.query.get(bookable_id)
        if not prof:
            return False
        ok, _ = range_is_bookable(prof.provider_id, start_at, end_at)
        return ok

    # Lifecycle hooks — all no-ops for the default bookable.
    @staticmethod
    def on_request(booking, domain_payload=None):
        pass

    @staticmethod
    def on_confirm(booking, domain_payload=None):
        pass

    @staticmethod
    def on_decline(booking, domain_payload=None):
        pass

    @staticmethod
    def on_cancel(booking, domain_payload=None):
        pass

    @staticmethod
    def on_complete(booking, domain_payload=None):
        pass

    @staticmethod
    def on_no_show(booking, domain_payload=None):
        pass

    @staticmethod
    def on_dispute_resolution(booking, resolution, domain_payload=None):
        pass


# Built-in registration — BI spec §5: register_bookable("service_provider", DefaultHandler)
register_bookable('service_provider', DefaultProviderHandler)
