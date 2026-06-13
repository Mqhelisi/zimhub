"""Integration tests for TicketHandler — per STAGE_3_SPEC.md §11.15.

The handler is the integration boundary between the TicketGenerator module and
PurchaseInterface. Silent breakage here would corrupt tickets / inventory in
production.

Covers happy paths:
  - resolve_listing
  - on_initiate (places hold, snapshots names + price, validates attendee count)
  - on_payment_confirmed (hold -> sold, mints exactly N HMAC-signed tickets)
  - on_cancel (releases hold without minting)
  - on_dispute_resolution (refunded: tickets voided, sold count reversed)

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_ticket_handler.py

Note: the production schema uses Postgres-specific types (UUID, JSONB,
SELECT FOR UPDATE). These tests skip cleanly if running against SQLite.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest


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
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1 FROM events LIMIT 1'))
        except Exception:
            pytest.skip('Stage 3 schema not migrated; run `python manage.py db-init` first.')
        yield db
        db.session.rollback()


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------
def _mk_promoter(db, suffix=None):
    from app.models import User, PromoterProfile
    from app.utils.passwords import hash_password
    suffix = suffix or uuid.uuid4().hex[:6]
    u = User(
        email=f'test-promoter-{suffix}@example.com',
        phone=f'+26377222{suffix[:4]}',
        password_hash=hash_password('Test123!'),
        name=f'Test Promoter {suffix}',
        is_buyer=True, is_promoter=True,
        password_reset_required=False,
    )
    db.session.add(u)
    db.session.flush()
    db.session.add(PromoterProfile(
        user_id=u.id, organisation_name=f'Test Promotions {suffix}',
        default_currency='USD',
    ))
    db.session.flush()
    return u


def _mk_buyer(db, suffix=None):
    from app.models import User
    from app.utils.passwords import hash_password
    suffix = suffix or uuid.uuid4().hex[:6]
    u = User(
        email=f'test-buyer-{suffix}@example.com',
        phone=f'+26377333{suffix[:4]}',
        password_hash=hash_password('Test123!'),
        name=f'Test Buyer {suffix}',
        is_buyer=True,
    )
    db.session.add(u)
    db.session.flush()
    return u


def _mk_event(db, promoter, *, mode='ticketed', status='active'):
    from app.modules.ticket_generator.models import Event
    now = datetime.now(timezone.utc)
    e = Event(
        promoter_id=promoter.id,
        title=f'Test Event {uuid.uuid4().hex[:6]}',
        description='Test', category='Music',
        start_at=now + timedelta(days=10),
        end_at=now + timedelta(days=10, hours=4),
        location='Test venue',
        status=status, mode=mode,
    )
    db.session.add(e)
    db.session.flush()
    return e


def _mk_ticket_type(db, event, *, name='General', price=Decimal('5.00'), qty=100):
    from app.modules.ticket_generator.models import TicketType
    tt = TicketType(
        event_id=event.id, name=name,
        price_usd=Decimal(str(price)), quantity_total=qty,
    )
    db.session.add(tt)
    db.session.flush()
    return tt


def _mk_purchase(db, *, buyer, seller, tt, quantity, payload):
    from app.modules.purchase_interface.models import Purchase
    unit = Decimal(str(tt.price_usd))
    total = (unit * Decimal(quantity)).quantize(Decimal('0.01'))
    p = Purchase(
        listing_type='event_ticket', listing_id=tt.id,
        seller_id=seller.id, buyer_id=buyer.id,
        quantity=quantity, unit_price_usd=unit, total_usd=total,
        currency='USD', status='awaiting_payment',
        domain_payload=payload,
        hold_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.session.add(p)
    db.session.flush()
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_resolve_listing_happy_path(db_ctx):
    db = db_ctx
    promoter = _mk_promoter(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, name='General', price=Decimal('5.00'), qty=200)

    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    info = TicketHandler.resolve_listing(
        tt.id, qty=3, domain_payload={'attendee_names': ['A', 'B', 'C']},
    )
    assert info['seller_id'] == promoter.id
    assert info['unit_price_usd'] == Decimal('5.00')
    assert info['currency'] == 'USD'
    assert info['quantity_available'] >= 3
    assert 'General' in info['label']


def test_resolve_listing_rejects_flyer_event(db_ctx):
    db = db_ctx
    from app.modules.purchase_interface.handlers import PurchaseHandlerError
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    event = _mk_event(db, promoter, mode='flyer')
    tt = _mk_ticket_type(db, event)  # shouldn't exist in reality, but defend.
    with pytest.raises(PurchaseHandlerError):
        TicketHandler.resolve_listing(tt.id, qty=1, domain_payload={})


def test_on_initiate_holds_inventory_and_snapshots(db_ctx):
    db = db_ctx
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, price=Decimal('5.00'), qty=10)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=2,
        payload={'attendee_names': ['Alice', 'Bob']},
    )

    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    TicketHandler.on_initiate(purchase, purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)

    assert tt.quantity_held == 2
    assert tt.quantity_sold == 0
    assert purchase.domain_payload['attendee_names'] == ['Alice', 'Bob']
    assert purchase.domain_payload['unit_price_usd_at_checkout'] == '5.00'


def test_on_initiate_rejects_wrong_attendee_count(db_ctx):
    db = db_ctx
    from app.modules.purchase_interface.handlers import PurchaseHandlerError
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=3,
        payload={'attendee_names': ['Only one']},
    )
    with pytest.raises(PurchaseHandlerError):
        TicketHandler.on_initiate(purchase, purchase.domain_payload)


def test_on_initiate_rejects_when_sold_out(db_ctx):
    db = db_ctx
    from app.modules.purchase_interface.handlers import PurchaseHandlerError
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, qty=1)
    tt.quantity_sold = 1  # already gone
    db.session.flush()
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=1,
        payload={'attendee_names': ['Latecomer']},
    )
    with pytest.raises(PurchaseHandlerError):
        TicketHandler.on_initiate(purchase, purchase.domain_payload)


def test_on_payment_confirmed_mints_n_tickets_and_signs_them(db_ctx):
    db = db_ctx
    from app.modules.ticket_generator.models import Ticket
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    from app.modules.ticket_generator.services.qr import verify_payload

    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, price=Decimal('5.00'), qty=10)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=3,
        payload={'attendee_names': ['A', 'B', 'C']},
    )
    TicketHandler.on_initiate(purchase, purchase.domain_payload)
    db.session.flush()

    # Simulate the state machine moving the purchase to awaiting_buyer_confirm.
    purchase.status = 'awaiting_buyer_confirmation'
    purchase.payment_ref = 'ECOCASH-TEST-123'

    refs = TicketHandler.on_payment_confirmed(purchase, purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)

    assert refs['refs']['ticket_count'] == 3
    minted = Ticket.query.filter(Ticket.purchase_id == purchase.id).all()
    assert len(minted) == 3
    names = sorted(t.attendee_name for t in minted)
    assert names == ['A', 'B', 'C']
    for t in minted:
        assert t.status == 'valid'
        assert t.price_usd == Decimal('5.00')
        assert t.payment_ref == 'ECOCASH-TEST-123'
        tid, ok = verify_payload(t.qr_code)
        assert ok is True
        assert tid == str(t.id)

    # Inventory: hold released, sold incremented.
    assert tt.quantity_held == 0
    assert tt.quantity_sold == 3


def test_on_cancel_releases_hold(db_ctx):
    db = db_ctx
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, qty=10)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=2,
        payload={'attendee_names': ['A', 'B']},
    )
    TicketHandler.on_initiate(purchase, purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)
    assert tt.quantity_held == 2

    TicketHandler.on_cancel(purchase, purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)
    assert tt.quantity_held == 0
    assert tt.quantity_sold == 0


def test_on_dispute_resolution_refunded_voids_tickets_and_reverses_stock(db_ctx):
    db = db_ctx
    from app.modules.ticket_generator.models import Ticket
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, qty=10)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=2,
        payload={'attendee_names': ['A', 'B']},
    )
    TicketHandler.on_initiate(purchase, purchase.domain_payload)
    db.session.flush()
    purchase.status = 'awaiting_buyer_confirmation'
    purchase.payment_ref = 'ECOCASH-DR-1'
    TicketHandler.on_payment_confirmed(purchase, purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)
    assert tt.quantity_sold == 2

    # Now the dispute resolves as 'refunded' — handler should void & reverse.
    TicketHandler.on_dispute_resolution(purchase, 'refunded', purchase.domain_payload)
    db.session.flush()
    db.session.refresh(tt)

    voided = Ticket.query.filter(Ticket.purchase_id == purchase.id).all()
    assert len(voided) == 2
    assert all(t.status == 'voided' for t in voided)
    assert tt.quantity_sold == 0


def test_on_dispute_resolution_completed_does_nothing(db_ctx):
    db = db_ctx
    from app.modules.ticket_generator.models import Ticket
    from app.modules.ticket_generator.services.ticket_handler import TicketHandler
    promoter = _mk_promoter(db)
    buyer = _mk_buyer(db)
    event = _mk_event(db, promoter)
    tt = _mk_ticket_type(db, event, qty=10)
    purchase = _mk_purchase(
        db, buyer=buyer, seller=promoter, tt=tt, quantity=1,
        payload={'attendee_names': ['Single']},
    )
    TicketHandler.on_initiate(purchase, purchase.domain_payload)
    db.session.flush()
    purchase.status = 'awaiting_buyer_confirmation'
    purchase.payment_ref = 'ECOCASH-OK'
    TicketHandler.on_payment_confirmed(purchase, purchase.domain_payload)
    db.session.flush()

    TicketHandler.on_dispute_resolution(purchase, 'completed', purchase.domain_payload)
    db.session.flush()

    tickets = Ticket.query.filter(Ticket.purchase_id == purchase.id).all()
    assert all(t.status == 'valid' for t in tickets)
