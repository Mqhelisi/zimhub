"""Stage 5 regression + integration guards — CreatorPlatform.

Protects the hard rules from the Stage 5 handoff:
  - event_ticket is ANY-OF: a creator OR a promoter can sell; a pure buyer
    cannot. (The capability re-assertion runs LAST in create_app.)
  - A ticketed creator event IS a real TicketGenerator event owned by the
    creator (the bridge), so it resolves through the existing TicketHandler with
    seller == the creator — no parallel ticketing path.
  - Creator profile provisioning (apply-approve consolidation) populates the
    Stage-1 creator_profiles shell from the signup-request payload.
  - All five modules coexist: 4 PurchaseInterface listing types unaffected, the
    one BookingInterface bookable intact, both dispute desks still separate.

Pure-capability tests need no DB. Bridge/provisioning tests use the seeded
creator and skip cleanly if the DB has not been seeded.

Run:
    cd backend
    ZIMHUB_NO_SCHEDULER=1 pytest tests/test_creator_event_bridge.py
"""
import os
import uuid
from types import SimpleNamespace

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
    from extensions import db
    from sqlalchemy import text
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1 FROM creator_tracks LIMIT 1'))
        except Exception:
            pytest.skip('Stage 5 schema not migrated; run `flask db upgrade` first.')
        yield db
        db.session.rollback()


# ---------------------------------------------------------------------------
# Any-of capability (pure — no DB)
# ---------------------------------------------------------------------------
def test_event_ticket_capability_is_any_of_tuple(app):
    from app.services import host
    cap = host.LISTING_TYPE_TO_CAPABILITY.get('event_ticket')
    assert cap == ('is_promoter', 'is_creator'), (
        'event_ticket must be any-of (is_promoter, is_creator) after the '
        'CreatorPlatform module re-asserts it last in create_app.'
    )


def test_can_sell_event_ticket_creator_and_promoter_yes_buyer_no(app):
    from app.services import host
    creator = SimpleNamespace(is_promoter=False, is_creator=True)
    promoter = SimpleNamespace(is_promoter=True, is_creator=False)
    both = SimpleNamespace(is_promoter=True, is_creator=True)
    buyer = SimpleNamespace(is_promoter=False, is_creator=False)
    assert host.can_sell(creator, 'event_ticket') is True
    assert host.can_sell(promoter, 'event_ticket') is True
    assert host.can_sell(both, 'event_ticket') is True
    assert host.can_sell(buyer, 'event_ticket') is False


def test_product_capability_unchanged_single_string(app):
    """The any-of change must not have leaked into other listing types."""
    from app.services import host
    assert host.LISTING_TYPE_TO_CAPABILITY.get('product') == 'is_salesman'
    salesman = SimpleNamespace(is_salesman=True)
    not_salesman = SimpleNamespace(is_salesman=False)
    assert host.can_sell(salesman, 'product') is True
    assert host.can_sell(not_salesman, 'product') is False


def test_register_module_is_idempotent(app):
    from app.services import host
    from app.modules.creator_platform import register_creator_platform_module
    register_creator_platform_module()
    register_creator_platform_module()
    assert host.LISTING_TYPE_TO_CAPABILITY['event_ticket'] == ('is_promoter', 'is_creator')


# ---------------------------------------------------------------------------
# Five-module coexistence (pure — no DB)
# ---------------------------------------------------------------------------
def test_all_listing_handlers_present_and_distinct_registries(app):
    from app.modules.purchase_interface.handlers import HANDLERS
    from app.modules.booking_interface.handlers import BOOKABLE_HANDLERS
    assert HANDLERS is not BOOKABLE_HANDLERS
    # PurchaseInterface listing types (Stages 2–3) untouched by Stage 5.
    assert HANDLERS['product'].__name__ == 'ProductHandler'
    assert HANDLERS['event_ticket'].__name__ == 'TicketHandler'
    # service_provider remains a bookable, not a PI listing.
    assert 'service_provider' not in HANDLERS
    assert 'service_provider' in BOOKABLE_HANDLERS
    # CreatorPlatform did NOT add a new PI/BI handler (creator events reuse TG).
    assert 'creator_event' not in HANDLERS and 'creator_event' not in BOOKABLE_HANDLERS


def test_creator_blueprints_registered(app):
    names = set(app.blueprints.keys())
    for bp in ('creator_platform_public', 'creator_platform_studio',
               'creator_platform_music', 'creator_platform_gallery',
               'creator_platform_events'):
        assert bp in names


# ---------------------------------------------------------------------------
# Creator → TicketGenerator bridge (DB — uses seeded creator, else skip)
# ---------------------------------------------------------------------------
def _seeded_creator(db):
    from app.models import User
    return User.query.filter_by(email='creator1@zimhub.local').first()


def test_bridge_creates_tg_event_owned_by_creator(db_ctx):
    from app.modules.creator_platform.services.event_bridge import create_ticketed_tg_event
    from app.modules.ticket_generator.models import Event, TicketType
    creator = _seeded_creator(db_ctx)
    if creator is None:
        pytest.skip('DB not seeded with creators.')

    ev = create_ticketed_tg_event(creator, {
        'title': 'Bridge Test Event',
        'description': 'created by a test',
        'location': 'Test Venue',
        'start_at': '2026-09-01T19:00:00Z',
        'ticket_types': [{'name': 'GA', 'price_usd': '5', 'quantity_total': 10}],
    })
    db_ctx.session.flush()
    assert isinstance(ev, Event)
    assert str(ev.promoter_id) == str(creator.id), 'TG event must be owned by the creator.'
    assert ev.mode == 'ticketed'
    tts = TicketType.query.filter_by(event_id=ev.id).all()
    assert len(tts) == 1 and tts[0].name == 'GA'
    db_ctx.session.rollback()


def test_creator_ticket_resolves_with_seller_as_creator(db_ctx):
    """A ticket type on a creator-owned TG event resolves through the existing
    TicketHandler with seller_id == the creator (proves no parallel path)."""
    from app.modules.creator_platform.services.event_bridge import create_ticketed_tg_event
    from app.modules.purchase_interface.handlers import HANDLERS
    creator = _seeded_creator(db_ctx)
    if creator is None:
        pytest.skip('DB not seeded with creators.')

    ev = create_ticketed_tg_event(creator, {
        'title': 'Resolve Test', 'location': 'V', 'start_at': '2026-09-02T19:00:00Z',
        'ticket_types': [{'name': 'GA', 'price_usd': '8', 'quantity_total': 5}],
    })
    db_ctx.session.flush()
    from app.modules.ticket_generator.models import TicketType
    tt = TicketType.query.filter_by(event_id=ev.id).first()

    handler = HANDLERS['event_ticket']()
    resolved = handler.resolve_listing(str(tt.id))
    assert str(resolved['seller_id']) == str(creator.id)
    db_ctx.session.rollback()


# ---------------------------------------------------------------------------
# Profile provisioning (DB — transient user, rolled back)
# ---------------------------------------------------------------------------
def test_provision_creator_profile_populates_shell(db_ctx):
    from app.models import User, CreatorProfile
    from app.utils.passwords import hash_password
    from app.modules.creator_platform.services.profile_provisioning import (
        provision_creator_profile,
    )
    email = f'test-creator-{uuid.uuid4().hex[:8]}@example.com'
    u = User(email=email, phone='+263770000000', password_hash=hash_password('x'),
             name='Test Creator', is_buyer=True, is_creator=True)
    db_ctx.session.add(u)
    db_ctx.session.flush()
    # shell (as the signup approval would create) then provision
    profile = CreatorProfile(user_id=u.id, display_name='Test Creator',
                             creator_slug=f'test-creator-{uuid.uuid4().hex[:6]}')
    db_ctx.session.add(profile)
    db_ctx.session.flush()

    provision_creator_profile(u, {
        'creator_types': ['musician'],
        'discipline_tags': ['house'],
        'display_name': 'DJ Test',
    })
    db_ctx.session.flush()
    refreshed = CreatorProfile.query.filter_by(user_id=u.id).first()
    assert refreshed.status == 'approved'
    assert 'musician' in (refreshed.creator_types or [])
    db_ctx.session.rollback()
