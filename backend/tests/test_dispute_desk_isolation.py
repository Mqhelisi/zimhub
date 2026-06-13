"""Dispute-desk isolation — /super/disputes (PurchaseInterface) vs
/super/booking-disputes (BookingInterface) are SEPARATE desks.

Acceptance step 72: the Stage 2 desk shows ONLY product + event_ticket
disputes; the Stage 4 desk shows ONLY booking disputes.

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_dispute_desk_isolation.py
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

try:
    import psycopg2  # noqa: F401
    _HAS_PG = True
except ImportError:
    _HAS_PG = False

os.environ.setdefault('ZIMHUB_NO_SCHEDULER', '1')

pytestmark = pytest.mark.skipif(not _HAS_PG, reason='psycopg2 not installed')


@pytest.fixture(scope='module')
def app():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def db_ctx(app):
    from extensions import db
    from sqlalchemy import text
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1 FROM booking_disputes LIMIT 1'))
            db.session.execute(text('SELECT 1 FROM disputes LIMIT 1'))
        except Exception:
            pytest.skip('Schemas not migrated; run `flask db upgrade` first.')
        yield db
        db.session.rollback()


def _mk_user(db, **flags):
    from app.models import User
    from app.utils.passwords import hash_password
    u = User(email=f'd-{uuid.uuid4().hex[:10]}@test.local', phone='+263770000005',
             password_hash=hash_password('x'), name='Desk User', city='Bulawayo',
             is_buyer=True, **flags)
    db.session.add(u)
    db.session.flush()
    return u


def test_tables_are_distinct(db_ctx):
    from app.modules.purchase_interface.models import PurchaseDispute
    from app.modules.booking_interface.models import BookingDispute
    assert PurchaseDispute.__tablename__ == 'disputes'
    assert BookingDispute.__tablename__ == 'booking_disputes'
    assert PurchaseDispute.__tablename__ != BookingDispute.__tablename__


def test_each_desk_lists_only_its_own_rows(db_ctx, app):
    """Create one open dispute in EACH system; each admin endpoint returns
    only its own and never the sibling's."""
    from app.modules.purchase_interface.models import (
        Purchase, PurchaseDispute,
    )
    from app.modules.booking_interface.models import Booking, BookingDispute

    seller = _mk_user(db_ctx, is_salesman=True)
    provider = _mk_user(db_ctx, is_provider=True)
    buyer = _mk_user(db_ctx)
    admin = _mk_user(db_ctx, is_super_admin=True)

    now = datetime.now(timezone.utc)

    purchase = Purchase(
        listing_type='product', listing_id=uuid.uuid4(),
        seller_id=seller.id, buyer_id=buyer.id, quantity=1,
        unit_price_usd=Decimal('10.00'), total_usd=Decimal('10.00'),
        status='disputed')
    db_ctx.session.add(purchase)
    db_ctx.session.flush()
    pi_disp = PurchaseDispute(purchase_id=purchase.id, raised_by=buyer.id,
                              raised_by_role='buyer',
                              reason='ISOLATION-PI never delivered',
                              status='open')
    db_ctx.session.add(pi_disp)

    booking = Booking(
        bookable_type='service_provider', bookable_id=uuid.uuid4(),
        provider_id=provider.id, requester_id=buyer.id,
        start_at=now - timedelta(days=1),
        end_at=now - timedelta(days=1) + timedelta(hours=1),
        duration_hours=Decimal('1.00'), status='disputed',
        expires_at=now - timedelta(days=1))
    db_ctx.session.add(booking)
    db_ctx.session.flush()
    bi_disp = BookingDispute(booking_id=booking.id, raised_by=buyer.id,
                             raised_by_role='requester',
                             reason='ISOLATION-BI provider never arrived',
                             status='open')
    db_ctx.session.add(bi_disp)
    db_ctx.session.flush()
    booking.dispute_id = bi_disp.id
    db_ctx.session.flush()

    client = app.test_client()
    from flask_jwt_extended import create_access_token
    with app.app_context():
        token = create_access_token(identity=str(admin.id))
    client.set_cookie('access_token_cookie', token)

    r_bi = client.get('/api/admin/booking-disputes?status=open')
    assert r_bi.status_code == 200
    bi_ids = {d['id'] for d in r_bi.get_json()['disputes']}
    bi_reasons = ' '.join(d['reason'] for d in r_bi.get_json()['disputes'])
    assert str(bi_disp.id) in bi_ids
    assert str(pi_disp.id) not in bi_ids
    assert 'ISOLATION-PI' not in bi_reasons

    r_pi = client.get('/api/admin/disputes?status=open')
    assert r_pi.status_code == 200
    pi_payload = r_pi.get_json()['disputes']
    pi_ids = {d['id'] for d in pi_payload}
    pi_reasons = ' '.join(d.get('reason') or '' for d in pi_payload)
    assert str(pi_disp.id) in pi_ids
    assert str(bi_disp.id) not in pi_ids
    assert 'ISOLATION-BI' not in pi_reasons


def test_bi_resolution_does_not_touch_purchases(db_ctx):
    """Resolving a booking dispute mutates only BI rows."""
    from app.modules.purchase_interface.models import Purchase
    from app.modules.booking_interface.models import Booking, BookingDispute
    from app.modules.booking_interface.services import resolve_dispute

    provider = _mk_user(db_ctx, is_provider=True)
    buyer = _mk_user(db_ctx)
    admin = _mk_user(db_ctx, is_super_admin=True)
    now = datetime.now(timezone.utc)

    booking = Booking(
        bookable_type='service_provider', bookable_id=uuid.uuid4(),
        provider_id=provider.id, requester_id=buyer.id,
        start_at=now - timedelta(days=2),
        end_at=now - timedelta(days=2) + timedelta(hours=1),
        duration_hours=Decimal('1.00'), status='disputed',
        expires_at=now - timedelta(days=2))
    db_ctx.session.add(booking)
    db_ctx.session.flush()
    d = BookingDispute(booking_id=booking.id, raised_by=buyer.id,
                       raised_by_role='requester', reason='x', status='open')
    db_ctx.session.add(d)
    db_ctx.session.flush()
    booking.dispute_id = d.id

    purchases_before = db_ctx.session.query(Purchase).count()
    resolve_dispute(dispute=d, admin=admin, resolution='completed', note='ok')
    assert d.status == 'resolved'
    assert booking.status == 'completed'
    assert db_ctx.session.query(Purchase).count() == purchases_before
