"""Integration tests for ServiceHandler — STAGE_4_SPEC.md §11.14.

The handler is the integration boundary between the Services section and
BookingInterface — silent breakage here would be high cost.

Covers:
  - resolve_bookable: the bookable is the SERVICE row; returns provider_id,
    timezone, label, pricing info; inactive/unknown services raise.
  - is_open: defers correctly to BI's availability resolution against the
    PROVIDER's calendar (rules, blocks, confirmed bookings, granularity).

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_service_handler.py
Requires a migrated Postgres (ARRAY/JSONB/FOR UPDATE) — skips otherwise.
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
            db.session.execute(text('SELECT 1 FROM provider_services LIMIT 1'))
        except Exception:
            pytest.skip('Stage 4 schema not migrated; run `flask db upgrade` first.')
        yield db
        db.session.rollback()


def _mk_provider(db, *, name='Test Provider', tz='Africa/Harare'):
    from app.models import User, ProviderProfile
    from app.utils.passwords import hash_password
    from app.modules.booking_interface.models import BIProviderProfile
    u = User(email=f'p-{uuid.uuid4().hex[:10]}@test.local', phone='+263770000001',
             password_hash=hash_password('x'), name=name, city='Bulawayo',
             is_buyer=True, is_provider=True)
    db.session.add(u)
    db.session.flush()
    db.session.add(ProviderProfile(user_id=u.id, trade='Plumber',
                                   suburbs_served=['Hillside'], timezone=tz))
    prof = BIProviderProfile(provider_id=u.id, display_name=name,
                             slug=f'test-{uuid.uuid4().hex[:8]}', timezone=tz)
    db.session.add(prof)
    db.session.flush()
    return u, prof


def _mk_service(db, provider, *, unit='flat', rate='25.00', status='active',
                name='Tap repair'):
    from app.modules.services_section.models import ProviderService
    s = ProviderService(provider_user_id=provider.id, name=name,
                        description='Test service.', pricing_unit=unit,
                        rate_usd=Decimal(rate), default_duration_minutes=60,
                        status=status)
    db.session.add(s)
    db.session.flush()
    return s


def _open_weekday_slot(weekday=0, hour=10, hours=1):
    """Next future occurrence of `weekday` at HH:00 Harare (=UTC+2)."""
    from zoneinfo import ZoneInfo
    hara = ZoneInfo('Africa/Harare')
    base = datetime.now(timezone.utc).astimezone(hara)
    days = (weekday - base.weekday()) % 7 or 7
    start_local = (base + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    s = start_local.astimezone(timezone.utc)
    return s, s + timedelta(hours=hours)


def _add_full_week_rules(db, provider):
    from app.modules.booking_interface.models import AvailabilityRule
    for wd in range(7):
        db.session.add(AvailabilityRule(provider_id=provider.id, weekday=wd,
                                        start_time=dt_time(8, 0),
                                        end_time=dt_time(17, 0)))
    db.session.flush()


# ---------------------------------------------------------------------------
# resolve_bookable
# ---------------------------------------------------------------------------
def test_resolve_bookable_returns_provider_and_pricing(db_ctx):
    from app.modules.services_section.services import ServiceHandler
    provider, _ = _mk_provider(db_ctx, name='Resolve Test')
    svc = _mk_service(db_ctx, provider, unit='per_hour', rate='20.00',
                      name='Pipe installation')
    info = ServiceHandler.resolve_bookable(svc.id)
    assert info['provider_id'] == provider.id
    assert info['timezone'] == 'Africa/Harare'
    assert info['pricing_unit'] == 'per_hour'
    assert Decimal(str(info['rate_usd'])) == Decimal('20.00')
    assert 'Pipe installation' in info['label']
    assert 'Resolve Test' in info['label']
    assert info['currency'] == 'USD'


def test_resolve_bookable_is_keyed_on_service_not_provider(db_ctx):
    """The bookable_id is the provider_services row id — passing the provider
    user id must fail."""
    from app.modules.services_section.services import ServiceHandler
    from app.modules.booking_interface.handlers import BookingHandlerError
    provider, _ = _mk_provider(db_ctx)
    _mk_service(db_ctx, provider)
    with pytest.raises(BookingHandlerError) as exc:
        ServiceHandler.resolve_bookable(provider.id)  # wrong key on purpose
    assert exc.value.code == 'unknown_bookable'


def test_resolve_bookable_rejects_archived_service(db_ctx):
    from app.modules.services_section.services import ServiceHandler
    from app.modules.booking_interface.handlers import BookingHandlerError
    provider, _ = _mk_provider(db_ctx)
    svc = _mk_service(db_ctx, provider, status='archived')
    with pytest.raises(BookingHandlerError) as exc:
        ServiceHandler.resolve_bookable(svc.id)
    assert exc.value.code == 'inactive_service'
    assert exc.value.http_status == 409


# ---------------------------------------------------------------------------
# is_open — defers to BI's availability resolution
# ---------------------------------------------------------------------------
def test_is_open_true_inside_rules(db_ctx):
    from app.modules.services_section.services import ServiceHandler
    provider, _ = _mk_provider(db_ctx)
    svc = _mk_service(db_ctx, provider)
    _add_full_week_rules(db_ctx, provider)
    s, e = _open_weekday_slot(weekday=2, hour=10)
    assert ServiceHandler.is_open(svc.id, s, e) is True


def test_is_open_false_outside_rules(db_ctx):
    from app.modules.services_section.services import ServiceHandler
    provider, _ = _mk_provider(db_ctx)
    svc = _mk_service(db_ctx, provider)
    _add_full_week_rules(db_ctx, provider)   # 08–17 only
    s, e = _open_weekday_slot(weekday=2, hour=20)  # 20:00 — outside
    assert ServiceHandler.is_open(svc.id, s, e) is False


def test_is_open_false_when_blocked(db_ctx):
    from app.modules.services_section.services import ServiceHandler
    from app.modules.booking_interface.models import AvailabilityBlock
    provider, _ = _mk_provider(db_ctx)
    svc = _mk_service(db_ctx, provider)
    _add_full_week_rules(db_ctx, provider)
    s, e = _open_weekday_slot(weekday=3, hour=11)
    db_ctx.session.add(AvailabilityBlock(provider_id=provider.id,
                                         start_at=s, end_at=e, reason='Away'))
    db_ctx.session.flush()
    assert ServiceHandler.is_open(svc.id, s, e) is False


def test_is_open_gates_all_services_on_one_provider_calendar(db_ctx):
    """A confirmed booking on service A blocks the same slot on service B —
    conflict detection is PROVIDER-level (the §5.3 'elegant trick')."""
    from app.modules.services_section.services import ServiceHandler
    from app.modules.booking_interface.models import Booking
    provider, _ = _mk_provider(db_ctx)
    svc_a = _mk_service(db_ctx, provider, name='Service A')
    svc_b = _mk_service(db_ctx, provider, name='Service B')
    _add_full_week_rules(db_ctx, provider)
    s, e = _open_weekday_slot(weekday=4, hour=9, hours=2)

    from app.models import User
    from app.utils.passwords import hash_password
    buyer = User(email=f'b-{uuid.uuid4().hex[:10]}@test.local',
                 phone='+263770000002', password_hash=hash_password('x'),
                 name='Buyer', city='Bulawayo', is_buyer=True)
    db_ctx.session.add(buyer)
    db_ctx.session.flush()

    db_ctx.session.add(Booking(
        bookable_type='service_provider', bookable_id=svc_a.id,
        provider_id=provider.id, requester_id=buyer.id,
        start_at=s, end_at=e, duration_hours=Decimal('2.00'),
        status='confirmed', expires_at=s))
    db_ctx.session.flush()

    assert ServiceHandler.is_open(svc_b.id, s, e) is False
    # Back-to-back is fine — half-open ranges.
    assert ServiceHandler.is_open(svc_b.id, e, e + timedelta(hours=1)) is True
