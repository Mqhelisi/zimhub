# CreatorPlatform module (Stage 5)

Authoritative spec: `docs/CreatorPlatform_Spec.md`. Host-integration boundary:
`docs/STAGE_5_SPEC.md`.

The Creators section of ZimHub. Owns its full surface; integrates with the host
through three narrow seams:

- **Apply-approve consolidation** — no standalone onboarding. A `creator`
  signup request flows through the Stage-1 `/super/signup-requests` inbox; on
  approval, `services/profile_provisioning.provision_creator_profile` populates
  the `creator_profile`.
- **Creator events reuse TicketGenerator** — a ticketed creator event IS a real
  TG event owned by the creator (`services/event_bridge`). The `event_ticket`
  PurchaseInterface handler, QR signing, gate scanning, and dispute desk are all
  reused unchanged.
- **`event_ticket` any-of capability** — `host.can_sell('event_ticket')` accepts
  `is_promoter` OR `is_creator` (re-asserted in this module's
  `register_creator_platform_module`, run last in `create_app`).

The persistent audio player is app-global (mounted above the router on the
frontend), so a track started on a creator page keeps playing across `/shop`,
`/events`, and `/services`.

Tables (all `creator_`-prefixed; `creator_id` == the creator's `user_id`):
`creator_tracks`, `creator_play_events`, `creator_gallery_collections`,
`creator_gallery_items`, `creator_events`.
