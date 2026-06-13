"""Events section — Stage 3 host-level glue.

Owns:
  - the unified public Events feed (`/api/events`)
  - the Promoter section's profile / dashboard endpoints
  - flyer-event create / edit / convert-to-ticketed
  - top events / top promoters ranking

Does NOT own ticket lifecycle, gate scan, or the ticketed-event CRUD —
those live in TicketGenerator.
"""
