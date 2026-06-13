"""CreatorPlatform module — Stage 5 (V1 capstone).

The most self-contained of the five ZimHub modules: it owns nearly its whole
surface (creator content models, type-aware public pages, music streaming,
galleries, the Creator Studio, and creator events). Its host-integration seams
are narrow and live in `services/`:

  - event_bridge.py        — ticketed creator events ARE real TicketGenerator
                             events owned by the creator (no parallel ticketing).
  - profile_provisioning.py — the signup-request approval hook that populates a
                             creator's profile (apply-approve consolidation).

Registration (called once from create_app, AFTER the TicketGenerator module so
the any-of capability wins): re-asserts `event_ticket` as any-of
(is_promoter OR is_creator) so creators sell tickets to their own events
without the full Promoter capability.
"""


def register_creator_platform_module():
    """Call from create_app() once. Idempotent.

    Re-asserts the any-of event_ticket capability LAST so it wins over the
    TicketGenerator module's boot-time `register_listing_type('event_ticket',
    'is_promoter')`. After this, host.can_sell('event_ticket') accepts a creator
    OR a promoter; a pure buyer holds neither.
    """
    # Imported lazily to avoid a circular import at package load (app.models →
    # this package's models → this __init__; host imports app.models).
    from app.services.host import register_listing_type
    register_listing_type('event_ticket', ('is_promoter', 'is_creator'))
