"""Stage 2 seed — per STAGE_2_SPEC.md §7.

Runs AFTER stage1_seed (cumulative). Adds:
  - Updates Stage 1's salesman1 (Mthuli's Phone Hub) with photo + banner + bio
  - A second Salesman: salesman2 (Nomsa's Boutique)
  - 10 products per Salesman (20 total) across categories
  - One Purchase in every state of the PurchaseInterface state machine
  - One open Dispute + one resolved (refunded) Dispute
  - Matching mock_messages

Idempotent: skips if salesman2 already exists.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from extensions import db
from app.models import (
    User, SalesmanProfile, Notification, MockMessage,
)
from app.modules.shop.models import Product
from app.modules.purchase_interface.models import (
    Purchase, PurchaseEvent, PurchaseDispute,
)
from app.utils.passwords import hash_password
from app.utils.slugify import slugify_unique


def utcnow():
    return datetime.now(timezone.utc)


# Picsum.photos serves deterministic placeholder images via /seed/<seed>/<w>/<h>
def _img(seed: str, w: int = 800, h: int = 600) -> str:
    return f'https://picsum.photos/seed/{seed}/{w}/{h}'


# ---------------------------------------------------------------------------
# Catalog — realistic Bulawayo-market style entries
# ---------------------------------------------------------------------------
MTHULI_CATALOG = [
    # (name, category, price, stock, description)
    ('Itel A70 — 64GB', 'Phones & Accessories', Decimal('72.00'), 14,
     'Budget Android with a 6.6" display and 5000mAh battery. Comes with charger, screen protector applied.'),
    ('Samsung A05s — 128GB', 'Phones & Accessories', Decimal('149.00'), 8,
     'Reliable mid-range phone. Dual SIM, 50MP camera, sealed box.'),
    ('Tecno Spark Go 2024', 'Phones & Accessories', Decimal('98.00'), 11,
     'Sealed unit, 90Hz display, 5000mAh battery. 12 months warranty.'),
    ('iPhone 11 — 64GB (Used, grade A)', 'Phones & Accessories', Decimal('220.00'), 3,
     'Pre-owned iPhone 11 in excellent condition. Battery health 88%. No scratches. Includes charger.'),
    ('20W USB-C Fast Charger (PD)', 'Phones & Accessories', Decimal('11.00'), 30,
     'Apple/Android compatible. PD 20W. 12-month replacement guarantee.'),
    ('Braided USB-C Cable 1.5m', 'Phones & Accessories', Decimal('5.00'), 50,
     'Heavy-duty braided cable. Supports fast charging up to 65W.'),
    ('Bluetooth Earphones — TWS Pro', 'Phones & Accessories', Decimal('18.00'), 22,
     'Compact in-ear wireless earphones. Up to 5h playtime per charge, plus 25h with charging case.'),
    ('Phone Screen Replacement — Voucher', 'Phones & Accessories', Decimal('40.00'), 15,
     'Walk-in repair voucher: Samsung A-series, Itel, Tecno. Same-day turnaround.'),
    ('Premium Tempered Glass (universal)', 'Phones & Accessories', Decimal('4.00'), 60,
     '9H hardness. Multiple sizes available — confirm model in WhatsApp.'),
    ('Powerbank 20,000mAh', 'Electronics', Decimal('22.00'), 12,
     '20,000mAh dual-port powerbank. PD + QC 3.0. Charges most phones 3-4 times.'),
]

NOMSA_CATALOG = [
    ('Ankara Wrap Skirt — Sunset', 'Clothing', Decimal('25.00'), 9,
     'Handmade in Bulawayo from 100% cotton ankara. Adjustable waist tie, hits mid-calf. Sizes 8-16.'),
    ('Kitenge Blazer — Cobalt Print', 'Clothing', Decimal('48.00'), 6,
     'Tailored blazer in bold kitenge print. Fully lined, two-button closure. Sizes 10-18.'),
    ('Plain Linen Shift Dress', 'Clothing', Decimal('32.00'), 11,
     'Easy-wear shift dress in breathable linen. Cream, terracotta, navy. Sizes 8-16.'),
    ('Handwoven Beaded Necklace', 'Beauty & Personal Care', Decimal('14.00'), 16,
     'Multi-strand beaded necklace by a Bulawayo artisan. Adjustable length 40-50cm.'),
    ('Leather Crossbody Bag — Sand', 'Clothing', Decimal('38.00'), 8,
     'Local genuine leather. Single main compartment + internal zip pocket. Adjustable strap.'),
    ('Hand-Stitched Slipper Loafers', 'Footwear', Decimal('30.00'), 12,
     'Comfortable slip-on loafers handmade by a CBD cobbler. Real leather upper. Sizes 36-42.'),
    ('Block-Print Tote Bag', 'Clothing', Decimal('12.00'), 25,
     'Heavy-canvas tote with hand-block-printed motif. Reinforced handles, perfect for the market.'),
    ('Cotton Headwrap — Floral', 'Clothing', Decimal('8.00'), 35,
     'Soft cotton headwrap, 1.8m long. Multiple colours available — confirm via WhatsApp.'),
    ('Shea Butter Body Cream (250ml)', 'Beauty & Personal Care', Decimal('9.00'), 28,
     'Locally made unscented shea butter cream. No parabens.'),
    ('Beaded Anklet Set (3 pcs)', 'Beauty & Personal Care', Decimal('7.00'), 40,
     'Set of three handmade beaded anklets in coordinating colours.'),
]


def _ensure_salesman2(now):
    """Create salesman2 (Nomsa) + profile. Returns the user."""
    existing = User.query.filter_by(email='salesman2@zimhub.local').first()
    if existing:
        return existing

    u = User(
        email='salesman2@zimhub.local',
        phone='+263772000204',
        password_hash=hash_password('Seller123!'),
        name='Nomsa Tshuma',
        suburb='Khumalo',
        city='Bulawayo',
        is_buyer=True,
        is_salesman=True,
        password_reset_required=False,
        created_at=now - timedelta(days=10),
    )
    db.session.add(u)
    db.session.flush()
    slug = slugify_unique(
        "Nomsa's Boutique",
        exists_fn=lambda s: db.session.query(SalesmanProfile.user_id)
                              .filter_by(shop_slug=s).first() is not None,
    )
    p = SalesmanProfile(
        user_id=u.id,
        shop_name="Nomsa's Boutique",
        shop_slug=slug,
        bio='Womenswear made in Bulawayo — ankara, kitenge, linen. Pickup in Khumalo or nationwide courier.',
        photo_url=_img('nomsa-shop-photo', 400, 400),
        banner_url=_img('nomsa-shop-banner', 1600, 500),
        pickup_delivery_policy='Pickup in Khumalo Mon–Sat. Bulawayo metro delivery $3 flat. Nationwide courier 1–3 days, paid by buyer.',
        default_currency='USD',
    )
    db.session.add(p)
    db.session.flush()
    return u


def _enrich_salesman1(salesman1):
    """Backfill avatar/banner/bio on Stage 1's salesman1."""
    p = salesman1.salesman_profile
    if p is None:
        return
    if not p.photo_url:
        p.photo_url = _img('mthuli-shop-photo', 400, 400)
    if not p.banner_url:
        p.banner_url = _img('mthuli-shop-banner', 1600, 500)
    if not p.bio:
        p.bio = 'Latest smartphones, accessories, and same-day screen repairs in Hillside. Honest prices, real warranties.'


def _create_products(salesman_user, catalog, seed_prefix):
    """Create the catalog for a Salesman if not already present."""
    existing = Product.query.filter(Product.salesman_user_id == salesman_user.id).count()
    if existing > 0:
        # Assume already seeded.
        return Product.query.filter(Product.salesman_user_id == salesman_user.id) \
                            .order_by(Product.created_at.asc()).all()
    products = []
    for i, (name, cat, price, stock, desc) in enumerate(catalog, start=1):
        p = Product(
            salesman_user_id=salesman_user.id,
            name=name,
            description=desc,
            category=cat,
            price_usd=price,
            stock_quantity=stock,
            stock_held=0,
            stock_sold=0,
            photos=[
                _img(f'{seed_prefix}-p{i}-a', 800, 600),
                _img(f'{seed_prefix}-p{i}-b', 800, 600),
            ],
            status='active',
        )
        db.session.add(p)
        products.append(p)
    db.session.flush()
    return products


# ---------------------------------------------------------------------------
# Purchase factory — creates a purchase + line items + events + does stock bookkeeping
# ---------------------------------------------------------------------------
def _make_items_payload(items_with_products):
    """items_with_products: [(product, qty), ...] -> snapshotted items list."""
    out = []
    for prod, qty in items_with_products:
        out.append({
            'product_id': str(prod.id),
            'qty': qty,
            'unit_price_usd': str(prod.price_usd),
            'name': prod.name,
            'photo': (prod.photos or [None])[0] if prod.photos else None,
        })
    return out


def _line_total(items_with_products):
    total = Decimal('0')
    for prod, qty in items_with_products:
        total += Decimal(str(prod.price_usd)) * Decimal(qty)
    return total.quantize(Decimal('0.01'))


def _log_event(purchase, from_status, to_status, actor_id, actor_role, note, when):
    e = PurchaseEvent(
        purchase_id=purchase.id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        actor_role=actor_role,
        note=note,
        created_at=when,
    )
    db.session.add(e)
    return e


def _create_purchase(*, state, salesman, buyer, items, created_at, hold_hours=24,
                     settle_hours=72, payment_ref=None, cancel_reason=None,
                     dispute_reason=None, dispute_resolution=None,
                     dispute_resolution_note=None, dispute_resolver=None):
    """Create one Purchase + PurchaseEvents + stock updates for the given state.

    `state` ∈ {'awaiting_payment','awaiting_buyer_confirmation','completed',
               'cancelled','expired','disputed_open','disputed_resolved'}

    For disputed_resolved, `dispute_resolution` ∈ {'completed','refunded','cancelled'}.

    Stock bookkeeping kept consistent:
      awaiting_payment: stock_held += qty
      awaiting_buyer_confirmation: stock_sold += qty (already moved from held)
      completed: stock_sold += qty
      cancelled / expired: no stock change (released or never reserved)
      disputed_open (after payment confirmed): stock_sold += qty (frozen)
      disputed_resolved → refunded: was sold, then restored — net zero stock change here
                       → completed: stock_sold += qty
                       → cancelled: held or sold reversed depending on prior path
    """
    total = _line_total(items)
    total_qty = sum(qty for _, qty in items)
    unit_price = (total / Decimal(total_qty)).quantize(Decimal('0.01'))

    payload_items = _make_items_payload(items)
    first_pid = items[0][0].id

    p = Purchase(
        listing_type='product',
        listing_id=first_pid,
        seller_id=salesman.id,
        buyer_id=buyer.id,
        quantity=total_qty,
        unit_price_usd=unit_price,
        total_usd=total,
        currency='USD',
        domain_payload={'items': payload_items},
        created_at=created_at,
        updated_at=created_at,
    )
    # ---- state-specific fields + stock ----
    db.session.add(p)
    db.session.flush()  # need p.id

    # Always create the initiation event
    _log_event(p, None, 'awaiting_payment', buyer.id, 'buyer',
               'Purchase initiated.', created_at)

    if state == 'awaiting_payment':
        p.status = 'awaiting_payment'
        p.hold_expires_at = created_at + timedelta(hours=hold_hours)
        for prod, qty in items:
            prod.stock_held = (prod.stock_held or 0) + qty

    elif state == 'awaiting_buyer_confirmation':
        p.status = 'awaiting_buyer_confirmation'
        seller_at = created_at + timedelta(hours=3)
        p.seller_confirmed_at = seller_at
        p.auto_complete_at = seller_at + timedelta(hours=settle_hours)
        p.payment_ref = payment_ref or 'ECOCASH-AB12C9'
        for prod, qty in items:
            prod.stock_sold = (prod.stock_sold or 0) + qty
        _log_event(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                   salesman.id, 'seller', 'Payment confirmed; goods delivered.', seller_at)
        p.updated_at = seller_at

    elif state == 'completed':
        seller_at = created_at + timedelta(hours=4)
        buyer_at = seller_at + timedelta(hours=20)
        p.status = 'completed'
        p.seller_confirmed_at = seller_at
        p.buyer_confirmed_at = buyer_at
        p.completed_at = buyer_at
        p.payment_ref = payment_ref or 'ECOCASH-77K9PX'
        for prod, qty in items:
            prod.stock_sold = (prod.stock_sold or 0) + qty
        _log_event(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                   salesman.id, 'seller', 'Payment confirmed; goods delivered.', seller_at)
        _log_event(p, 'awaiting_buyer_confirmation', 'completed',
                   buyer.id, 'buyer', 'Receipt confirmed.', buyer_at)
        p.updated_at = buyer_at

    elif state == 'cancelled':
        p.status = 'cancelled'
        cancelled_at = created_at + timedelta(hours=2)
        _log_event(p, 'awaiting_payment', 'cancelled',
                   buyer.id, 'buyer', cancel_reason or 'Changed my mind.', cancelled_at)
        # Stock not held in seed (never moved during create above) → no release needed.
        p.updated_at = cancelled_at

    elif state == 'expired':
        p.status = 'expired'
        # hold_expires_at in the past
        p.hold_expires_at = created_at + timedelta(hours=hold_hours)
        expired_at = p.hold_expires_at + timedelta(minutes=2)
        _log_event(p, 'awaiting_payment', 'expired',
                   None, 'system', 'Hold window elapsed.', expired_at)
        p.updated_at = expired_at

    elif state == 'disputed_open':
        # Disputed after payment confirmed (buyer says goods not received).
        seller_at = created_at + timedelta(hours=3)
        dispute_at = seller_at + timedelta(hours=14)
        p.status = 'disputed'
        p.seller_confirmed_at = seller_at
        p.payment_ref = payment_ref or 'ECOCASH-44JK22'
        p.auto_complete_at = None  # frozen on dispute
        for prod, qty in items:
            prod.stock_sold = (prod.stock_sold or 0) + qty

        _log_event(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                   salesman.id, 'seller', 'Payment confirmed; goods delivered.', seller_at)

        dispute = PurchaseDispute(
            purchase_id=p.id,
            raised_by=buyer.id,
            raised_by_role='buyer',
            reason=dispute_reason or 'Item received does not match what was advertised. Asking for return + refund.',
            status='open',
            created_at=dispute_at,
        )
        db.session.add(dispute)
        db.session.flush()
        p.dispute_id = dispute.id
        _log_event(p, 'awaiting_buyer_confirmation', 'disputed',
                   buyer.id, 'buyer',
                   f'Dispute raised: {dispute.reason[:160]}', dispute_at)
        p.updated_at = dispute_at

    elif state == 'disputed_resolved':
        # Payment confirmed, dispute raised, admin resolves.
        resolution = dispute_resolution or 'refunded'
        seller_at = created_at + timedelta(hours=3)
        dispute_at = seller_at + timedelta(hours=12)
        resolved_at = dispute_at + timedelta(hours=8)

        # Pre-dispute: payment was confirmed, stock_sold += qty
        for prod, qty in items:
            prod.stock_sold = (prod.stock_sold or 0) + qty

        _log_event(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                   salesman.id, 'seller', 'Payment confirmed; goods delivered.', seller_at)

        dispute = PurchaseDispute(
            purchase_id=p.id,
            raised_by=buyer.id,
            raised_by_role='buyer',
            reason=dispute_reason or 'Wrong size delivered. Returning the item.',
            status='resolved',
            resolution=resolution,
            resolution_note=dispute_resolution_note or 'Verified with the buyer; refund agreed via WhatsApp.',
            resolved_by=dispute_resolver.id if dispute_resolver else None,
            created_at=dispute_at,
            resolved_at=resolved_at,
        )
        db.session.add(dispute)
        db.session.flush()
        p.dispute_id = dispute.id
        p.payment_ref = payment_ref or 'ECOCASH-12MQ7Z'

        _log_event(p, 'awaiting_buyer_confirmation', 'disputed',
                   buyer.id, 'buyer',
                   f'Dispute raised: {dispute.reason[:160]}', dispute_at)

        # Resolution effect on stock
        if resolution == 'refunded':
            # Restore stock_sold
            for prod, qty in items:
                prod.stock_sold = max(0, (prod.stock_sold or 0) - qty)
            p.status = 'refunded'
        elif resolution == 'cancelled':
            for prod, qty in items:
                prod.stock_sold = max(0, (prod.stock_sold or 0) - qty)
            p.status = 'cancelled'
        else:  # completed
            p.status = 'completed'
            p.completed_at = resolved_at

        resolver_id = dispute_resolver.id if dispute_resolver else None
        _log_event(p, 'disputed', p.status, resolver_id, 'admin',
                   f'Dispute resolved as {p.status}.', resolved_at)
        p.updated_at = resolved_at
    else:
        raise ValueError(f'Unknown state: {state}')

    return p


# ---------------------------------------------------------------------------
# Notifications & mock_messages
# ---------------------------------------------------------------------------
def _seed_notification(*, user_id, kind, title, body, when, metadata=None, read=False):
    db.session.add(Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        metadata_json=metadata or {},
        read_at=when if read else None,
        created_at=when,
    ))


def _seed_mock_messages_for_purchase(p, salesman, buyer, when):
    """One whatsapp link from buyer→seller for each initiated purchase."""
    label = (p.domain_payload or {}).get('items', [{}])[0].get('name', 'item')
    short = (
        f"ZimHub: Hi {salesman.name.split(' ')[0]}, this is about my purchase: {label}. "
        f"Total ${p.total_usd}. Please share your Ecocash so I can settle. "
        f"Ref: {str(p.id)[:8]}"
    )
    db.session.add(MockMessage(
        channel='whatsapp',
        recipient=salesman.phone,
        subject=None,
        body=short,
        payload={'template': 'purchase_initiated_buyer_to_seller',
                 'purchase_id': str(p.id)},
        created_at=when,
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run():
    now = utcnow()

    # Idempotency: if salesman2 already exists, we assume Stage 2 was seeded.
    if User.query.filter_by(email='salesman2@zimhub.local').first():
        print('• Stage 2 seed appears to have already run (salesman2 exists). Skipping.')
        return

    admin = User.query.filter_by(email='admin@zimhub.local').first()
    salesman1 = User.query.filter_by(email='salesman1@zimhub.local').first()
    buyers = [User.query.filter_by(email=f'buyer{i}@zimhub.local').first()
              for i in range(1, 6)]
    if not all([admin, salesman1] + buyers):
        print('• Stage 1 users missing — run Stage 1 seed first.')
        return

    # ---------------- Salesman2 ----------------
    salesman2 = _ensure_salesman2(now)
    _enrich_salesman1(salesman1)

    # ---------------- Catalogs ----------------
    s1_products = _create_products(salesman1, MTHULI_CATALOG, 'mthuli')
    s2_products = _create_products(salesman2, NOMSA_CATALOG, 'nomsa')
    by_name_s1 = {p.name: p for p in s1_products}
    by_name_s2 = {p.name: p for p in s2_products}

    # ---------------- Purchases ----------------
    # Each tuple: (state, salesman, buyer, [(product, qty), ...], hours-ago)
    # Spec breakdown:
    #   awaiting_payment:               2
    #   awaiting_buyer_confirmation:    2
    #   completed:                      3
    #   cancelled:                      1
    #   expired:                        1
    #   disputed_open:                  1
    #   disputed_resolved (refunded):   1
    plan = [
        # awaiting_payment ×2 — buyers committed, settling over WhatsApp
        dict(state='awaiting_payment', salesman=salesman1, buyer=buyers[0],
             items=[(by_name_s1['Itel A70 — 64GB'], 1)], hours_ago=4),
        dict(state='awaiting_payment', salesman=salesman2, buyer=buyers[1],
             items=[(by_name_s2['Ankara Wrap Skirt — Sunset'], 1),
                    (by_name_s2['Cotton Headwrap — Floral'], 2)], hours_ago=2),

        # awaiting_buyer_confirmation ×2 — payment landed, awaiting receipt
        dict(state='awaiting_buyer_confirmation', salesman=salesman1, buyer=buyers[2],
             items=[(by_name_s1['Bluetooth Earphones — TWS Pro'], 1)],
             hours_ago=12),
        dict(state='awaiting_buyer_confirmation', salesman=salesman2, buyer=buyers[3],
             items=[(by_name_s2['Leather Crossbody Bag — Sand'], 1)],
             hours_ago=8),

        # completed ×3
        dict(state='completed', salesman=salesman1, buyer=buyers[0],
             items=[(by_name_s1['Premium Tempered Glass (universal)'], 2),
                    (by_name_s1['Braided USB-C Cable 1.5m'], 1)],
             hours_ago=72),  # 3 days ago
        dict(state='completed', salesman=salesman2, buyer=buyers[4],
             items=[(by_name_s2['Hand-Stitched Slipper Loafers'], 1)],
             hours_ago=140),  # 5-ish days ago
        dict(state='completed', salesman=salesman1, buyer=buyers[1],
             items=[(by_name_s1['20W USB-C Fast Charger (PD)'], 1),
                    (by_name_s1['Braided USB-C Cable 1.5m'], 1)],
             hours_ago=200),  # 8-ish days ago

        # cancelled ×1
        dict(state='cancelled', salesman=salesman2, buyer=buyers[2],
             items=[(by_name_s2['Plain Linen Shift Dress'], 1)],
             hours_ago=30,
             cancel_reason='Buyer changed mind before paying.'),

        # expired ×1 — hold window passed without payment
        dict(state='expired', salesman=salesman1, buyer=buyers[3],
             items=[(by_name_s1['Powerbank 20,000mAh'], 1)],
             hours_ago=48),  # > 24h ago, hold_expires_at in past

        # disputed (open) ×1 — payment confirmed, buyer says wrong item
        dict(state='disputed_open', salesman=salesman1, buyer=buyers[4],
             items=[(by_name_s1['Samsung A05s — 128GB'], 1)],
             hours_ago=36,
             dispute_reason='Phone arrived with a cracked back cover. Asked seller to swap; waiting on response.'),

        # disputed (resolved → refunded) ×1
        dict(state='disputed_resolved', salesman=salesman2, buyer=buyers[2],
             items=[(by_name_s2['Kitenge Blazer — Cobalt Print'], 1)],
             hours_ago=90,
             dispute_reason='Wrong size sent. Returning the blazer.',
             dispute_resolution='refunded',
             dispute_resolution_note='Confirmed with both parties via WhatsApp. Refund agreed; admin closing as refunded.',
             dispute_resolver=admin),
    ]

    counts = {}
    purchase_ids_by_state = {}
    for cfg in plan:
        created_at = now - timedelta(hours=cfg['hours_ago'])
        kwargs = {k: v for k, v in cfg.items() if k != 'hours_ago'}
        p = _create_purchase(created_at=created_at, **kwargs)

        # Tally for the seed report. Map disputed_resolved → its terminal state.
        if cfg['state'] == 'disputed_open':
            counts['disputed (open)'] = counts.get('disputed (open)', 0) + 1
        elif cfg['state'] == 'disputed_resolved':
            counts['disputed (resolved)'] = counts.get('disputed (resolved)', 0) + 1
        else:
            counts[cfg['state']] = counts.get(cfg['state'], 0) + 1
        purchase_ids_by_state.setdefault(cfg['state'], []).append(p.id)

        # Seed notifications + mock messages for visibility in the UI.
        label = cfg['items'][0][0].name + (
            f" (+{len(cfg['items']) - 1} more)" if len(cfg['items']) > 1 else ''
        )
        # purchase_initiated to both parties
        _seed_notification(
            user_id=cfg['salesman'].id,
            kind='purchase_initiated',
            title=f"New purchase: {label}",
            body=f"A buyer committed to buy {label}. Coordinate over WhatsApp.",
            when=created_at,
            metadata={'purchase_id': str(p.id)},
            read=cfg['state'] not in ('awaiting_payment',),
        )
        _seed_notification(
            user_id=cfg['buyer'].id,
            kind='purchase_initiated',
            title=f"Purchase initiated: {label}",
            body=f"You committed to buy {label}. Total ${p.total_usd}.",
            when=created_at,
            metadata={'purchase_id': str(p.id)},
            read=cfg['state'] not in ('awaiting_payment',),
        )
        _seed_mock_messages_for_purchase(p, cfg['salesman'], cfg['buyer'], created_at)

        # Stage-specific extra notifications
        if cfg['state'] == 'awaiting_buyer_confirmation':
            _seed_notification(
                user_id=cfg['buyer'].id,
                kind='payment_confirmed',
                title=f"Payment confirmed: {label}",
                body='The seller confirmed payment and delivered the goods. Confirm receipt to finalise.',
                when=created_at + timedelta(hours=3),
                metadata={'purchase_id': str(p.id)},
            )
        elif cfg['state'] == 'completed':
            for uid in (cfg['salesman'].id, cfg['buyer'].id):
                _seed_notification(
                    user_id=uid,
                    kind='purchase_completed',
                    title=f"Purchase completed: {label}",
                    body=f"Total ${p.total_usd}. Thanks for using ZimHub.",
                    when=created_at + timedelta(hours=24),
                    metadata={'purchase_id': str(p.id)},
                    read=True,
                )
        elif cfg['state'] == 'cancelled':
            for uid in (cfg['salesman'].id, cfg['buyer'].id):
                _seed_notification(
                    user_id=uid,
                    kind='purchase_cancelled',
                    title=f"Purchase cancelled: {label}",
                    body=cfg.get('cancel_reason') or 'This purchase was cancelled.',
                    when=created_at + timedelta(hours=2),
                    metadata={'purchase_id': str(p.id)},
                )
        elif cfg['state'] == 'expired':
            for uid in (cfg['salesman'].id, cfg['buyer'].id):
                _seed_notification(
                    user_id=uid,
                    kind='purchase_expired',
                    title=f"Purchase expired: {label}",
                    body='The payment hold expired. The reservation was released.',
                    when=created_at + timedelta(hours=25),
                    metadata={'purchase_id': str(p.id)},
                )
        elif cfg['state'] == 'disputed_open':
            for uid in (cfg['salesman'].id, admin.id):
                _seed_notification(
                    user_id=uid,
                    kind='purchase_disputed',
                    title=f"Dispute raised: {label}",
                    body='The buyer raised a dispute. Open the dispute desk to review.',
                    when=created_at + timedelta(hours=17),
                    metadata={'purchase_id': str(p.id)},
                )
        elif cfg['state'] == 'disputed_resolved':
            for uid in (cfg['salesman'].id, cfg['buyer'].id):
                _seed_notification(
                    user_id=uid,
                    kind='dispute_resolved',
                    title=f"Dispute resolved: {label}",
                    body=f"Resolution: {cfg.get('dispute_resolution')}. {cfg.get('dispute_resolution_note', '')}",
                    when=created_at + timedelta(hours=23),
                    metadata={'purchase_id': str(p.id)},
                    read=True,
                )

    db.session.commit()

    # ---------------- Report ----------------
    print('')
    print('✓ Stage 2 seed complete (on top of Stage 1).')
    print('')
    print('Salesmen with catalogs:')
    print(f"  salesman1@zimhub.local — Mthuli's Phone Hub (Phones & Accessories) — {len(s1_products)} products")
    print(f"  salesman2@zimhub.local — Nomsa's Boutique (Clothing) — {len(s2_products)} products  (password: Seller123!)")
    print('')
    print('Purchases seeded by state:')
    pretty_order = [
        'awaiting_payment', 'awaiting_buyer_confirmation', 'completed',
        'cancelled', 'expired', 'disputed (open)', 'disputed (resolved)',
    ]
    for k in pretty_order:
        if k in counts:
            print(f"  {k:32s} {counts[k]}")
    print('')
    total_msgs_added = len(plan)  # 1 mock_message per purchase (WhatsApp deep-link)
    print(f"Mock messages added: {total_msgs_added}")
    print('')
    print('Login as any seeded user (see Stage 1 output for passwords) and walk through.')
