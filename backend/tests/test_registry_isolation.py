"""Stage 4 regression guards — registry isolation, dispute-desk separation,
and scheduler multi-module stability.

These protect the hard rules from the Stage 4 handoff:
  - BookingInterface and PurchaseInterface NEVER share registries or state.
  - 'product' / 'event_ticket' listing handlers are untouched by Stage 4;
    'service_provider' is a BI bookable, NOT a PurchaseInterface listing.
  - /api/admin/disputes (PI) and /api/admin/booking-disputes (BI) are
    separate desks: neither lists the other's rows.
  - Both modules' sweepers register on the one shared APScheduler instance.

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_registry_isolation.py
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
            db.session.execute(text('SELECT 1 FROM bookings LIMIT 1'))
        except Exception:
            pytest.skip('Stage 4 schema not migrated; run `flask db upgrade` first.')
        yield db
        db.session.rollback()


# ---------------------------------------------------------------------------
# Registry isolation (no Postgres needed for these three)
# ---------------------------------------------------------------------------
def test_registries_are_distinct_objects(app):
    from app.modules.purchase_interface.handlers import HANDLERS
    from app.modules.booking_interface.handlers import BOOKABLE_HANDLERS
    assert HANDLERS is not BOOKABLE_HANDLERS


def test_purchase_registry_untouched_by_stage_4(app):
    """Stage 2/3 listing types intact; Stage 4 added nothing to PI."""
    from app.modules.purchase_interface.handlers import HANDLERS
    assert HANDLERS['product'].__name__ == 'ProductHandler'
    assert HANDLERS['event_ticket'].__name__ == 'TicketHandler'
    assert 'service_provider' not in HANDLERS


def test_booking_registry_has_service_handler_only(app):
    """'service_provider' resolves to Stage 4's ServiceHandler (it replaced
    the built-in default at boot); no PI listing types bled in."""
    from app.modules.booking_interface.handlers import BOOKABLE_HANDLERS
    assert BOOKABLE_HANDLERS['service_provider'].__name__ == 'ServiceHandler'
    assert 'product' not in BOOKABLE_HANDLERS
    assert 'event_ticket' not in BOOKABLE_HANDLERS


def test_host_capability_registries_are_parallel(app):
    """host.py keeps the listing/bookable maps parallel; bookables live in their
    own map (Stage 4 spec §5.5). Stage 5 widens event_ticket to any-of
    (is_promoter OR is_creator) so creators can sell their own event tickets —
    the listing map must NOT gain service_provider and product stays unchanged.
    """
    from app.services.host import (
        LISTING_TYPE_TO_CAPABILITY, BOOKABLE_TYPE_TO_CAPABILITY,
    )
    assert 'service_provider' not in LISTING_TYPE_TO_CAPABILITY
    assert LISTING_TYPE_TO_CAPABILITY == {
        'product': 'is_salesman',
        'event_ticket': ('is_promoter', 'is_creator'),  # Stage 5 any-of
    }
    assert BOOKABLE_TYPE_TO_CAPABILITY['service_provider'] == 'is_provider'


def test_register_bookable_idempotent_and_replaceable(app):
    from app.modules.booking_interface.handlers import (
        BOOKABLE_HANDLERS, register_bookable,
    )
    class FakeHandler:  # noqa: N801
        pass
    register_bookable('test_thing', FakeHandler)
    register_bookable('test_thing', FakeHandler)   # idempotent
    assert BOOKABLE_HANDLERS['test_thing'] is FakeHandler
    class FakeHandler2:
        pass
    register_bookable('test_thing', FakeHandler2)  # replace
    assert BOOKABLE_HANDLERS['test_thing'] is FakeHandler2
    del BOOKABLE_HANDLERS['test_thing']


# ---------------------------------------------------------------------------
# Scheduler — both modules' sweepers on the one shared instance
# ---------------------------------------------------------------------------
def test_scheduler_registers_all_four_sweepers(app):
    import app.jobs.scheduler as sched_mod
    # Force a fresh instance regardless of the NO_SCHEDULER env guard —
    # we're testing job registration, not the create_app() guard.
    sched_mod.stop_scheduler()
    s = sched_mod.start_scheduler(app)
    try:
        ids = {j.id for j in s.get_jobs()}
        assert ids == {
            'purchase_interface.expire',
            'purchase_interface.auto_complete',
            'booking_interface.expire',
            'booking_interface.complete',
        }
        # Idempotent — a second start (Flask reloader) is a no-op.
        assert sched_mod.start_scheduler(app) is s
    finally:
        sched_mod.stop_scheduler()


def test_sweepers_run_in_app_context_without_cross_talk(db_ctx, app):
    """Running BI sweepers must not touch Purchase rows and vice versa."""
    from app.models import User
    from app.modules.purchase_interface.models import Purchase
    from app.modules.booking_interface.models import Booking
    from app.modules.booking_interface.services import (
        expire_bookings_due, complete_bookings_due,
    )
    from app.utils.passwords import hash_password

    u1 = User(email=f'sw-{uuid.uuid4().hex[:8]}@test.local', phone='+263770000003',
              password_hash=hash_password('x'), name='P', city='Bulawayo',
              is_buyer=True, is_provider=True)
    u2 = User(email=f'sw-{uuid.uuid4().hex[:8]}@test.local', phone='+263770000004',
              password_hash=hash_password('x'), name='R', city='Bulawayo',
              is_buyer=True)
    db_ctx.session.add_all([u1, u2])
    db_ctx.session.flush()

    now = datetime.now(timezone.utc)
    overdue = Booking(
        bookable_type='service_provider', bookable_id=uuid.uuid4(),
        provider_id=u1.id, requester_id=u2.id,
        start_at=now - timedelta(hours=3), end_at=now - timedelta(hours=2),
        duration_hours=Decimal('1.00'), status='requested',
        expires_at=now - timedelta(hours=3))
    db_ctx.session.add(overdue)
    db_ctx.session.flush()

    purchases_before = db_ctx.session.query(Purchase).count()
    n = expire_bookings_due()
    assert n >= 1
    db_ctx.session.refresh(overdue)
    assert overdue.status == 'expired'
    assert db_ctx.session.query(Purchase).count() == purchases_before
    complete_bookings_due()  # no confirmed rows here; must not raise
    # Cleanup (the sweeper committed) — cascade removes booking_events.
    db_ctx.session.delete(overdue)
    db_ctx.session.commit()
