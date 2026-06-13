"""Booking state-machine integration tests — BI spec §4 / §12.

Covers the rules acceptance steps 62/64/66/67/68 exercise from the UI:
  - request: pending does NOT lock; same slot can take multiple requests
  - accept: locks; auto-declines overlapping pendings (slot_taken);
    409 slot_taken when a confirmed clash exists
  - cancel: works before start, blocked after start
  - no-show: only after start; complete: only after end (manual path)
  - own-profile booking rejected; outside-availability rejected

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_booking_state_machine.py
"""
import os
import uuid
from datetime import datetime, time as dt_time, timedelta, timezone
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
            db.session.execute(text('SELECT 1 FROM bookings LIMIT 1'))
        except Exception:
            pytest.skip('Stage 4 schema not migrated; run `flask db upgrade` first.')
        yield db
        db.session.rollback()


def _mk_user(db, **flags):
    from app.models import User
    from app.utils.passwords import hash_password
    u = User(email=f'sm-{uuid.uuid4().hex[:10]}@test.local',
             phone='+263770000006', password_hash=hash_password('x'),
             name='SM User', city='Bulawayo', is_buyer=True, **flags)
    db.session.add(u)
    db.session.flush()
    return u


def _mk_full_provider(db):
    """Provider with BI profile, full-week 08–17 rules, and one service."""
    from app.models import ProviderProfile
    from app.modules.booking_interface.models import (
        BIProviderProfile, AvailabilityRule,
    )
    from app.modules.services_section.models import ProviderService
    u = _mk_user(db, is_provider=True)
    db.session.add(ProviderProfile(user_id=u.id, trade='Plumber',
                                   suburbs_served=['Hillside'],
                                   timezone='Africa/Harare'))
    db.session.add(BIProviderProfile(provider_id=u.id, display_name='SM Provider',
                                     slug=f'sm-{uuid.uuid4().hex[:8]}',
                                     timezone='Africa/Harare'))
    for wd in range(7):
        db.session.add(AvailabilityRule(provider_id=u.id, weekday=wd,
                                        start_time=dt_time(8, 0),
                                        end_time=dt_time(17, 0)))
    svc = ProviderService(provider_user_id=u.id, name='Tap repair',
                          description='Test.', pricing_unit='flat',
                          rate_usd=Decimal('25.00'),
                          default_duration_minutes=60, status='active')
    db.session.add(svc)
    db.session.flush()
    return u, svc


def _future_slot(hour=10, days=3, hours=1):
    from zoneinfo import ZoneInfo
    hara = ZoneInfo('Africa/Harare')
    local = (datetime.now(timezone.utc).astimezone(hara)
             + timedelta(days=days)).replace(hour=hour, minute=0,
                                             second=0, microsecond=0)
    s = local.astimezone(timezone.utc)
    return s, s + timedelta(hours=hours)


def test_request_then_accept_locks_and_autodeclines_overlaps(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, accept_booking,
    )
    provider, svc = _mk_full_provider(db_ctx)
    buyer_a = _mk_user(db_ctx)
    buyer_b = _mk_user(db_ctx)
    s, e = _future_slot(hour=10)

    # Pending requests do NOT lock — two requesters can hold the same slot.
    a = request_booking(requester=buyer_a, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=s, end_at=e,
                        message='A first')
    b = request_booking(requester=buyer_b, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=s, end_at=e,
                        message='B second')
    assert a.status == b.status == 'requested'
    assert a.quoted_rate_usd == Decimal('25.00')   # flat snapshot

    # Accept A — B auto-declines with slot_taken.
    accept_booking(booking=a, provider=provider)
    db_ctx.session.flush()
    assert a.status == 'confirmed'
    assert b.status == 'declined'
    assert b.cancel_reason == 'slot_taken'
    assert any(ev.note == 'slot_taken' and ev.actor_role == 'system'
               for ev in b.events)


def test_accept_with_confirmed_clash_returns_slot_taken(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, accept_booking, BookingStateError,
    )
    provider, svc = _mk_full_provider(db_ctx)
    buyer_a = _mk_user(db_ctx)
    buyer_b = _mk_user(db_ctx)
    s, e = _future_slot(hour=11, days=4)

    a = request_booking(requester=buyer_a, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=s, end_at=e)
    b = request_booking(requester=buyer_b, bookable_type='service_provider',
                        bookable_id=svc.id,
                        start_at=s, end_at=e + timedelta(hours=1))
    accept_booking(booking=a, provider=provider)
    # b was auto-declined by a's acceptance (overlap) — craft a fresh pending
    # that overlaps the now-confirmed range to hit the 409 path directly.
    c = request_booking(requester=buyer_b, bookable_type='service_provider',
                        bookable_id=svc.id,
                        start_at=e, end_at=e + timedelta(hours=1))
    # widen c's range in-place to overlap (simulating a race where the slot
    # was free at request time but confirmed before accept)
    c.start_at = s
    db_ctx.session.flush()
    with pytest.raises(BookingStateError) as exc:
        accept_booking(booking=c, provider=provider)
    assert exc.value.code == 'slot_taken'
    assert exc.value.http_status == 409
    assert c.status == 'requested'   # stays requested (§4)


def test_request_validations(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, BookingStateError,
    )
    provider, svc = _mk_full_provider(db_ctx)
    s, e = _future_slot(hour=9, days=5)

    # Own profile guard.
    with pytest.raises(BookingStateError) as exc:
        request_booking(requester=provider, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=s, end_at=e)
    assert exc.value.code == 'own_profile'

    # Outside availability (20:00 > 17:00 close).
    buyer = _mk_user(db_ctx)
    s2, e2 = _future_slot(hour=20, days=5)
    with pytest.raises(BookingStateError) as exc:
        request_booking(requester=buyer, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=s2, end_at=e2)
    assert exc.value.code == 'slot_unavailable'
    assert exc.value.http_status == 409

    # Past slot.
    past = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(BookingStateError):
        request_booking(requester=buyer, bookable_type='service_provider',
                        bookable_id=svc.id, start_at=past,
                        end_at=past + timedelta(hours=1))


def test_cancel_before_start_and_blocked_after(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, accept_booking, cancel_booking, BookingStateError,
    )
    provider, svc = _mk_full_provider(db_ctx)
    buyer = _mk_user(db_ctx)
    s, e = _future_slot(hour=14, days=6)
    bk = request_booking(requester=buyer, bookable_type='service_provider',
                         bookable_id=svc.id, start_at=s, end_at=e)
    accept_booking(booking=bk, provider=provider)
    cancel_booking(booking=bk, user=buyer, reason='Plans changed')
    assert bk.status == 'cancelled'
    assert bk.cancelled_by == 'requester'

    # A booking already past its start cannot self-cancel.
    bk2 = request_booking(requester=buyer, bookable_type='service_provider',
                          bookable_id=svc.id,
                          start_at=s + timedelta(hours=2),
                          end_at=e + timedelta(hours=2))
    accept_booking(booking=bk2, provider=provider)
    bk2.start_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_ctx.session.flush()
    with pytest.raises(BookingStateError) as exc:
        cancel_booking(booking=bk2, user=provider)
    assert exc.value.code == 'too_late'


def test_no_show_and_manual_complete_timing(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, accept_booking, mark_no_show, mark_complete,
        BookingStateError,
    )
    provider, svc = _mk_full_provider(db_ctx)
    buyer = _mk_user(db_ctx)
    s, e = _future_slot(hour=8, days=2, hours=2)
    bk = request_booking(requester=buyer, bookable_type='service_provider',
                         bookable_id=svc.id, start_at=s, end_at=e)
    accept_booking(booking=bk, provider=provider)

    # Too early for both actions while the slot is in the future.
    with pytest.raises(BookingStateError) as exc:
        mark_no_show(booking=bk, provider=provider)
    assert exc.value.code == 'too_early'
    with pytest.raises(BookingStateError) as exc:
        mark_complete(booking=bk, provider=provider)   # step 68 / §11.8
    assert exc.value.code == 'too_early'

    # After start (but before end): no-show OK, complete still rejected.
    bk.start_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    bk.end_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    db_ctx.session.flush()
    with pytest.raises(BookingStateError):
        mark_complete(booking=bk, provider=provider)

    # After end: complete succeeds.
    bk.end_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_ctx.session.flush()
    mark_complete(booking=bk, provider=provider)
    assert bk.status == 'completed'
    assert bk.completed_at is not None


def test_dispute_freezes_and_admin_resolves(db_ctx):
    from app.modules.booking_interface.services import (
        request_booking, accept_booking, mark_no_show, raise_dispute,
        resolve_dispute, complete_bookings_due,
    )
    provider, svc = _mk_full_provider(db_ctx)
    buyer = _mk_user(db_ctx)
    admin = _mk_user(db_ctx, is_super_admin=True)
    s, e = _future_slot(hour=15, days=2)
    bk = request_booking(requester=buyer, bookable_type='service_provider',
                         bookable_id=svc.id, start_at=s, end_at=e)
    accept_booking(booking=bk, provider=provider)
    bk.start_at = datetime.now(timezone.utc) - timedelta(hours=2)
    bk.end_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_ctx.session.flush()
    mark_no_show(booking=bk, provider=provider)
    d = raise_dispute(booking=bk, user=buyer, reason='I was home all day.')
    assert bk.status == 'disputed'
    resolve_dispute(dispute=d, admin=admin, resolution='completed',
                    note='Provider evidence accepted.')
    assert bk.status == 'completed'
    assert d.status == 'resolved'
