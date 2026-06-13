# TicketGenerator module

Stage 3 implementation of the event ticketing module per
`docs/TICKET_GENERATOR_SPEC.md`.

**Owns:** events, ticket_types, tickets, gatemen, checkins.

**Does not own:** purchases, purchase_events, disputes — those live in
PurchaseInterface and are linked via `tickets.purchase_id`.

**Plugs in as:** `register_purchasable('event_ticket', TicketHandler)` at app
boot.

For module internals, follow `docs/TICKET_GENERATOR_SPEC.md` verbatim.
For Stage 3's flyer-event extension and the unified events feed, see
`docs/STAGE_3_SPEC.md` §5.3 and the sibling `events_section/` module.
