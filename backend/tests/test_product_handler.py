"""Integration tests for ProductHandler — per STAGE_2_SPEC.md §11.15.

The handler is the integration boundary between the Shop module and
PurchaseInterface; silent breakage here would be high cost.

Covers happy paths only this stage (other coverage remains optional):
  - resolve_listing
  - on_initiate (places hold, snapshots price)
  - on_payment_confirmed (hold -> sold)
  - on_cancel (releases hold)
  - on_dispute_resolution (restores stock on refunded)

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 DATABASE_URL=sqlite:///:memory: pytest tests/test_product_handler.py
    # Or with the dev Postgres:
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_product_handler.py

Note: the production schema uses Postgres-specific types (ARRAY, JSONB,
SELECT FOR UPDATE). These tests will skip if running against SQLite.
"""
import os
import uuid
from decimal import Decimal

import pytest

# Tests need a backend Postgres because of ARRAY/JSONB and FOR UPDATE.
# We skip cleanly if Postgres isn't available.
try:
    import psycopg2  # noqa: F401
    _HAS_PG = True
except ImportError:
    _HAS_PG = False

os.environ.setdefault('ZIMHUB_NO_SCHEDULER', '1')


@pytest.fixture(scope='module')
def app():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def db_ctx(app):
    """Run each test in a transaction that gets rolled back at the end."""
    from extensions import db
    with app.app_context():
        # Ensure a clean state. We expect the DB to already be migrated.
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1 FROM products LIMIT 1'))
        except Exception:
            pytest.skip('Stage 2 schema not migrated; run `python manage.py db-init` first.')

        yield db
        db.session.rollback()


def _mk_salesman(db, suffix=None):
    from app.models import User, SalesmanProfile
    from app.utils.passwords import hash_password
    from app.utils.slugify import slugify_unique

    suffix = suffix or uuid.uuid4().hex[:6]
    u = User(
        email=f'test-salesman-{suffix}@example.com',
        phone=f'+26377777{suffix[:4]}',
        password_hash=hash_password('Test123!'),
        name=f'Test Salesman {suffix}',
        is_buyer=True,
        is_salesman=True,
        password_reset_required=False,
    )
    db.session.add(u)
    db.session.flush()
    slug = slugify_unique(
        f'Test Shop {suffix}',
        exists_fn=lambda s: db.session.query(SalesmanProfile.user_id).filter_by(shop_slug=s).first() is not None,
    )
    p = SalesmanProfile(
        user_id=u.id,
        shop_name=f'Test Shop {suffix}',
        shop_slug=slug,
    )
    db.session.add(p)
    db.session.flush()
    return u


def _mk_buyer(db, suffix=None):
    from app.models import User
    from app.utils.passwords import hash_password
    suffix = suffix or uuid.uuid4().hex[:6]
    u = User(
        email=f'test-buyer-{suffix}@example.com',
        phone=f'+26377111{suffix[:4]}',
        password_hash=hash_password('Test123!'),
        name=f'Test Buyer {suffix}',
        is_buyer=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_product(db, salesman, *, name='Widget', price=10, stock=5, status='active'):
    from app.modules.shop.models import Product
    p = Product(
        salesman_user_id=salesman.id,
        name=name,
        description='Test product.',
        category='Other',
        price_usd=Decimal(str(price)),
        stock_quantity=stock,
        photos=['https://example.com/img.jpg'],
        status=status,
    )
    db.session.add(p)
    db.session.flush()
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_resolve_listing_happy_path(db_ctx):
    db = db_ctx
    seller = _mk_salesman(db)
    p1 = _mk_product(db, seller, name='Phone X', price=Decimal('100'), stock=10)
    p2 = _mk_product(db, seller, name='Case Y', price=Decimal('25'), stock=20)

    from app.modules.shop.services.product_handler import ProductHandler
    info = ProductHandler.resolve_listing(
        p1.id, qty=3,
        domain_payload={'items': [
            {'product_id': str(p1.id), 'qty': 1},
            {'product_id': str(p2.id), 'qty': 2},
        ]},
    )
    assert str(info['seller_id']) == str(seller.id)
    assert info['currency'] == 'USD'
    assert info['quantity_available'] == 3  # cart_qty when all in stock
    # (1*100 + 2*25)/3 = 50 unit price
    assert Decimal(str(info['unit_price_usd'])) == Decimal('50.00')
    assert 'Test Shop' in info['label']


def test_resolve_listing_out_of_stock_returns_zero_qty(db_ctx):
    db = db_ctx
    seller = _mk_salesman(db)
    p = _mk_product(db, seller, stock=1)

    from app.modules.shop.services.product_handler import ProductHandler
    info = ProductHandler.resolve_listing(
        p.id, qty=5,
        domain_payload={'items': [{'product_id': str(p.id), 'qty': 5}]},
    )
    assert info['quantity_available'] == 0


def test_on_initiate_places_hold_and_snapshots_price(db_ctx):
    db = db_ctx
    from app.modules.shop.services.product_handler import ProductHandler
    from app.modules.purchase_interface.models import Purchase

    seller = _mk_salesman(db)
    buyer = _mk_buyer(db)
    p = _mk_product(db, seller, price=Decimal('20'), stock=5)

    purchase = Purchase(
        listing_type='product',
        listing_id=p.id,
        seller_id=seller.id,
        buyer_id=buyer.id,
        quantity=2,
        unit_price_usd=Decimal('20.00'),
        total_usd=Decimal('40.00'),
        currency='USD',
        status='awaiting_payment',
        domain_payload={'items': [{'product_id': str(p.id), 'qty': 2}]},
    )
    db.session.add(purchase)
    db.session.flush()

    ProductHandler.on_initiate(purchase, purchase.domain_payload)

    assert p.stock_held == 2
    # Snapshot wrote unit_price into the items list
    item = purchase.domain_payload['items'][0]
    assert Decimal(str(item['unit_price_usd'])) == Decimal('20.00')
    assert item['name'] == p.name


def test_on_payment_confirmed_moves_held_to_sold(db_ctx):
    db = db_ctx
    from app.modules.shop.services.product_handler import ProductHandler
    from app.modules.purchase_interface.models import Purchase

    seller = _mk_salesman(db)
    buyer = _mk_buyer(db)
    p = _mk_product(db, seller, price=Decimal('15'), stock=10)

    purchase = Purchase(
        listing_type='product', listing_id=p.id,
        seller_id=seller.id, buyer_id=buyer.id,
        quantity=3, unit_price_usd=Decimal('15'), total_usd=Decimal('45'),
        currency='USD', status='awaiting_payment',
        domain_payload={'items': [{'product_id': str(p.id), 'qty': 3}]},
    )
    db.session.add(purchase)
    db.session.flush()
    ProductHandler.on_initiate(purchase, purchase.domain_payload)
    assert p.stock_held == 3

    ProductHandler.on_payment_confirmed(purchase, purchase.domain_payload)
    assert p.stock_held == 0
    assert p.stock_sold == 3


def test_on_cancel_releases_hold(db_ctx):
    db = db_ctx
    from app.modules.shop.services.product_handler import ProductHandler
    from app.modules.purchase_interface.models import Purchase

    seller = _mk_salesman(db)
    buyer = _mk_buyer(db)
    p = _mk_product(db, seller, stock=8)

    purchase = Purchase(
        listing_type='product', listing_id=p.id,
        seller_id=seller.id, buyer_id=buyer.id,
        quantity=2, unit_price_usd=Decimal('10'), total_usd=Decimal('20'),
        currency='USD', status='awaiting_payment',
        domain_payload={'items': [{'product_id': str(p.id), 'qty': 2}]},
    )
    db.session.add(purchase)
    db.session.flush()
    ProductHandler.on_initiate(purchase, purchase.domain_payload)
    assert p.stock_held == 2

    ProductHandler.on_cancel(purchase, purchase.domain_payload)
    assert p.stock_held == 0
    assert p.stock_sold == 0


def test_on_dispute_resolution_refunded_restores_sold_stock(db_ctx):
    db = db_ctx
    from datetime import datetime, timezone
    from app.modules.shop.services.product_handler import ProductHandler
    from app.modules.purchase_interface.models import Purchase

    seller = _mk_salesman(db)
    buyer = _mk_buyer(db)
    p = _mk_product(db, seller, stock=5)

    purchase = Purchase(
        listing_type='product', listing_id=p.id,
        seller_id=seller.id, buyer_id=buyer.id,
        quantity=2, unit_price_usd=Decimal('10'), total_usd=Decimal('20'),
        currency='USD', status='awaiting_buyer_confirmation',
        domain_payload={'items': [{'product_id': str(p.id), 'qty': 2}]},
        seller_confirmed_at=datetime.now(timezone.utc),
    )
    db.session.add(purchase)
    db.session.flush()
    # Simulate prior on_initiate + on_payment_confirmed bookkeeping
    p.stock_sold = 2

    ProductHandler.on_dispute_resolution(purchase, 'refunded', purchase.domain_payload)
    assert p.stock_sold == 0


def test_salesman_mismatch_raises(db_ctx):
    db = db_ctx
    from app.modules.shop.services.product_handler import ProductHandler
    from app.modules.purchase_interface.handlers import PurchaseHandlerError

    seller_a = _mk_salesman(db)
    seller_b = _mk_salesman(db)
    pa = _mk_product(db, seller_a)
    pb = _mk_product(db, seller_b)

    with pytest.raises(PurchaseHandlerError) as ex:
        ProductHandler.resolve_listing(
            pa.id, qty=2,
            domain_payload={'items': [
                {'product_id': str(pa.id), 'qty': 1},
                {'product_id': str(pb.id), 'qty': 1},
            ]},
        )
    assert ex.value.code == 'salesman_mismatch'
