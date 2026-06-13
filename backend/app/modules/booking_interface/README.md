# BookingInterface

Reusable time-booking module. **Authoritative spec: `docs/BOOKING_INTERFACE_SPEC.md`.**

The sibling of PurchaseInterface — same module shape and host-integration
philosophy, but a booking succeeds purely by **mutual agreement** (provider
accepting a request). No money handshake, no proof-of-purchase; rates are
informational and payment happens off-platform.

- Models: `bi_provider_profiles`, `availability_rules`, `availability_blocks`,
  `bookings`, `booking_events`, `booking_disputes`. (Table names for
  provider-profiles/disputes are prefixed to avoid colliding with the host's
  and PurchaseInterface's tables; **column names match the spec verbatim**.)
- State machine: requested → confirmed/declined/cancelled/expired →
  completed/no_show, with optional `disputed` (admin resolves).
- No double-booking: enforced at **accept** with `SELECT … FOR UPDATE`;
  clashing pending requests auto-decline (`slot_taken`).
- Sweepers (60 s, shared APScheduler): expiry + completion.
- Handler registry: `register_bookable(bookable_type, handler_cls)` —
  independent of PurchaseInterface's registry. Stage 4's services_section
  registers `'service_provider'` → `ServiceHandler` (the bookable is the
  **catalog service**, conflict detection gates on the provider's calendar).
- Host seam consumed: `current_user`, `is_provider`, `is_dispute_admin`,
  `notify`, `whatsapp_link`, `send`, `config`.
