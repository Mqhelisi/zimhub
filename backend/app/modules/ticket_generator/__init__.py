"""TicketGenerator module — Stage 3.

Owns:
  - events / ticket_types / tickets / gatemen / checkins tables
  - the `TicketHandler` plugged into PurchaseInterface as
    `listing_type='event_ticket'`
  - Promoter admin endpoints under /api/promoter/* (events/ticket types/gatemen)
  - Buyer ticket endpoints under /api/my/tickets and /api/tickets/*
  - Gate scanning under /api/gate/* (bearer-token auth — the ONE non-cookie
    surface in ZimHub, per Stage 3 §5.5)
  - Public event detail under /api/events/:id (the unified feed lives in
    events_section)

Registration with PurchaseInterface happens via `register_ticket_generator_module`
which create_app() calls at boot, mirroring the Shop module's pattern.
"""
from app.modules.purchase_interface import register_purchasable
from .services.ticket_handler import TicketHandler


def register_ticket_generator_module():
    """Call from create_app() once. Idempotent."""
    from app.services.host import register_listing_type
    register_listing_type('event_ticket', 'is_promoter')
    register_purchasable('event_ticket', TicketHandler)
