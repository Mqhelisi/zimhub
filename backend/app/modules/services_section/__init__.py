"""Services section — host-level glue around BookingInterface (Stage 4).

Owns: the provider_services catalog, the 'service_provider' BookingInterface
handler, Provider admin endpoints, public discovery, and provider ranking.
Does NOT own booking lifecycle, availability rules, or conflict detection —
those are BookingInterface's domain.
"""


def register_services_module():
    """Called from create_app() after blueprints are registered. Registers the
    ServiceHandler against BookingInterface's SEPARATE registry (mirrors how
    Stages 2/3 registered their PurchaseInterface listing handlers)."""
    from app.modules.booking_interface import register_bookable
    from app.services.host import register_bookable_type
    from .services import ServiceHandler

    register_bookable('service_provider', ServiceHandler)
    register_bookable_type('service_provider', 'is_provider')
