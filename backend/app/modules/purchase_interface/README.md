# PurchaseInterface module

This is the reusable purchase + settlement subsystem for ZimHub. The
authoritative spec lives at `docs/PURCHASE_INTERFACE_SPEC.md` at the repo root.

**Module layout:**

```
purchase_interface/
├── __init__.py             # exports register_purchasable, PurchaseHandlerError
├── handlers.py             # the pluggable handler registry
├── models/
│   └── purchase.py         # Purchase, PurchaseEvent, PurchaseDispute
├── services/
│   └── state_machine.py    # transitions + sweepers + notifications + WA links
└── routes/
    ├── purchases.py        # /api/purchases/*  and  /api/my/purchases
    └── disputes.py         # /api/admin/disputes/*
```

**To plug a new domain in:**

1. Define your Listing model.
2. Implement a handler class with: `resolve_listing`, `on_initiate`,
   `on_payment_confirmed`, `on_cancel`, `on_complete`, `on_dispute_resolution`.
3. Call `register_purchasable("<your_type>", YourHandler)` at app boot.
4. Add `'<your_type>': '<capability_flag>'` to `LISTING_TYPE_TO_CAPABILITY` in
   `app/services/host.py`.

See `app/modules/shop/services/product_handler.py` for a worked example.
