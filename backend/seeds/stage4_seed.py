"""Stage 4 seed — per STAGE_4_SPEC.md §7.1. Runs AFTER stage3_seed.

Creates (on top of Stages 1–3, never altering their rows):
  - provider1@zimhub.local fleshed out as "Themba Plumbing" + a NEW
    provider2@zimhub.local "Sarah Mobile Hair"
  - 6 services across the two providers covering all 4 pricing units
  - recurring weekly availability per provider + 4 one-off blocks
  - Bookings in EVERY BookingInterface state: requested(2), confirmed(2),
    declined(1), cancelled(1), expired(1), completed(3), no_show(1),
    disputed open(1) and disputed→resolved(1)
  - matching mock_messages + notifications via the host seam

Time-shifting: requested/confirmed land in the upcoming week (inside the
providers' open hours so calendars look right); terminal states land in the
past 30 days so the ranking has signal. Buyers rotate across Stage 1's
seeded accounts.

Idempotent: skips if provider2@zimhub.local already exists.
"""
from datetime import datetime, time as dt_time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from extensions import db
from app.models import User, ProviderProfile
from app.utils.passwords import hash_password
from app.utils.slugify import slugify_unique
from app.services import host
from app.modules.booking_interface.models import (
    BIProviderProfile, AvailabilityRule, AvailabilityBlock,
    Booking, BookingEvent, BookingDispute,
)
from app.modules.services_section.models import ProviderService


HARARE = ZoneInfo('Africa/Harare')


def utcnow():
    return datetime.now(timezone.utc)


def _next_local(weekday: int, hour: int, *, weeks_ahead=0, base=None):
    """Next future occurrence (≥ tomorrow) of weekday at HH:00 Harare time,
    returned as UTC."""
    base = base or utcnow().astimezone(HARARE)
    days_ahead = (weekday - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    local = (base + timedelta(days=days_ahead + weeks_ahead * 7)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def _past_local(days_ago: int, hour: int):
    """`days_ago` days back at HH:00 Harare time, as UTC."""
    local = (utcnow().astimezone(HARARE) - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    return local.astimezone(timezone.utc)


def _mk_booking(*, service, requester, start_at, hours, status,
                message=None, created_shift_hours=2, **extra):
    rate = Decimal(str(service.rate_usd))
    if service.pricing_unit == 'per_hour':
        quoted = (rate * Decimal(hours)).quantize(Decimal('0.01'))
    elif service.pricing_unit == 'per_km':
        quoted = None
    else:
        quoted = rate.quantize(Decimal('0.01'))
    end_at = start_at + timedelta(hours=hours)
    b = Booking(
        bookable_type='service_provider',
        bookable_id=service.id,
        provider_id=service.provider_user_id,
        requester_id=requester.id,
        start_at=start_at, end_at=end_at,
        duration_hours=Decimal(str(hours)).quantize(Decimal('0.01')),
        status=status,
        message=message,
        quoted_rate_usd=quoted,
        domain_payload={
            'service_id': str(service.id),
            'buyer_notes': message or '',
            'buyer_phone_at_request': requester.phone,
            'distance_km': extra.pop('distance_km', None),
        },
        expires_at=extra.pop('expires_at', start_at),
        **extra,
    )
    b.created_at = start_at - timedelta(hours=max(created_shift_hours, 1),
                                        minutes=0)
    db.session.add(b)
    db.session.flush()
    db.session.add(BookingEvent(booking_id=b.id, from_status=None,
                                to_status='requested',
                                actor_id=requester.id, actor_role='requester'))
    return b


def _event(b, frm, to, actor_id, role, note=None):
    db.session.add(BookingEvent(booking_id=b.id, from_status=frm,
                                to_status=to, actor_id=actor_id,
                                actor_role=role, note=note))


def run():
    if User.query.filter_by(email='provider2@zimhub.local').first():
        print('• Stage 4 seed appears to have already run (provider2 exists). Skipping.')
        return

    # ---------------- Providers ----------------
    themba = User.query.filter_by(email='provider1@zimhub.local').first()
    if not themba:
        raise RuntimeError('Stage 1 seed must run first (provider1 missing).')

    sarah = User(
        email='provider2@zimhub.local',
        phone='+263772000204',
        password_hash=hash_password('Seller123!'),
        name='Sarah Mlilo',
        suburb='Hillside',
        city='Bulawayo',
        is_buyer=True,
        is_provider=True,
        password_reset_required=False,
    )
    db.session.add(sarah)
    db.session.flush()
    db.session.add(ProviderProfile(
        user_id=sarah.id, trade='Hairdresser',
        bio='Mobile braiding and styling — I come to you, anywhere in Bulawayo.',
        suburbs_served=['Hillside', 'Khumalo', 'Suburbs'],
        default_currency='USD', timezone='Africa/Harare',
    ))

    def _slug_exists(s):
        return db.session.query(BIProviderProfile.id).filter_by(slug=s).first() is not None

    themba_bi = BIProviderProfile(
        provider_id=themba.id, display_name='Themba Plumbing',
        slug=slugify_unique('Themba Plumbing', exists_fn=_slug_exists),
        bio=themba.provider_profile.bio if themba.provider_profile else None,
        timezone='Africa/Harare',
    )
    db.session.add(themba_bi)
    sarah_bi = BIProviderProfile(
        provider_id=sarah.id, display_name='Sarah Mobile Hair',
        slug=slugify_unique('Sarah Mobile Hair', exists_fn=_slug_exists),
        bio='Mobile braiding and styling — I come to you, anywhere in Bulawayo.',
        timezone='Africa/Harare',
    )
    db.session.add(sarah_bi)
    db.session.flush()

    # ---------------- Services (6, all 4 pricing units) ----------------
    def svc(provider, name, desc, unit, rate, dur):
        s = ProviderService(provider_user_id=provider.id, name=name,
                            description=desc, pricing_unit=unit,
                            rate_usd=Decimal(rate),
                            default_duration_minutes=dur, status='active')
        db.session.add(s)
        return s

    tap_repair = svc(themba, 'Tap repair',
                     'Fix leaking or stiff taps — kitchen, bathroom, or yard. Parts quoted separately.',
                     'flat', '25.00', 60)
    pipe_install = svc(themba, 'Pipe installation',
                       'New piping runs and replacements for geysers, sinks, and outdoor lines.',
                       'per_hour', '20.00', 120)
    bathroom = svc(themba, 'Full bathroom plumbing',
                   'Complete bathroom rough-in and fit-off. Day-rate; materials quoted separately.',
                   'per_day', '80.00', 480)
    braiding = svc(sarah, 'Hair braiding (at your home)',
                   'Box braids, cornrows, and twists done at your place. Hair extensions available.',
                   'flat', '35.00', 120)
    styling = svc(sarah, 'Hair styling',
                  'Wash, blow-dry, and styling for events or everyday looks.',
                  'per_hour', '15.00', 60)
    callout = svc(sarah, 'Home call-out',
                  'Travel to your home anywhere in Bulawayo — billed by distance.',
                  'per_km', '0.80', None)
    db.session.flush()

    # ---------------- Recurring availability ----------------
    # Themba: Mon–Fri 08:00–17:00, Sat 09:00–13:00 (Harare time)
    for wd in range(0, 5):
        db.session.add(AvailabilityRule(provider_id=themba.id, weekday=wd,
                                        start_time=dt_time(8, 0),
                                        end_time=dt_time(17, 0)))
    db.session.add(AvailabilityRule(provider_id=themba.id, weekday=5,
                                    start_time=dt_time(9, 0),
                                    end_time=dt_time(13, 0)))
    # Sarah: Tue–Sat 10:00–18:00
    for wd in range(1, 6):
        db.session.add(AvailabilityRule(provider_id=sarah.id, weekday=wd,
                                        start_time=dt_time(10, 0),
                                        end_time=dt_time(18, 0)))

    # ---------------- One-off blocks (4) ----------------
    blocks = [
        AvailabilityBlock(provider_id=themba.id,
                          start_at=_next_local(2, 14, weeks_ahead=1),
                          end_at=_next_local(2, 17, weeks_ahead=1),
                          reason='Away from work'),
        AvailabilityBlock(provider_id=themba.id,
                          start_at=_past_local(12, 9),
                          end_at=_past_local(12, 13),
                          reason='Family event'),
        AvailabilityBlock(provider_id=sarah.id,
                          start_at=_next_local(4, 10, weeks_ahead=1),
                          end_at=_next_local(4, 14, weeks_ahead=1),
                          reason='Supplier run — restocking extensions'),
        AvailabilityBlock(provider_id=sarah.id,
                          start_at=_past_local(20, 10),
                          end_at=_past_local(20, 18),
                          reason='Family wedding'),
    ]
    db.session.add_all(blocks)

    # ---------------- Buyers (rotate Stage 1 accounts) ----------------
    buyers = [User.query.filter_by(email=f'buyer{i}@zimhub.local').first()
              for i in range(1, 6)]
    buyers = [b for b in buyers if b]
    if len(buyers) < 5:
        raise RuntimeError('Stage 1 buyers missing.')
    b1, b2, b3, b4, b5 = buyers

    now = utcnow()
    mock_count_before = _mock_count()

    # ---------------- Bookings in EVERY state ----------------
    # requested (2) — upcoming week, inside open hours, expires at start.
    r1 = _mk_booking(service=tap_repair, requester=b1,
                     start_at=_next_local(0, 9), hours=1, status='requested',
                     message='Kitchen tap leaking under the sink.')
    _notify_pair(r1, 'booking_requested', to_provider=True)
    r2 = _mk_booking(service=styling, requester=b2,
                     start_at=_next_local(3, 14), hours=2, status='requested',
                     message='Styling for a Saturday wedding — trial run first?')
    _notify_pair(r2, 'booking_requested', to_provider=True)

    # confirmed (2) — upcoming week.
    c1 = _mk_booking(service=pipe_install, requester=b3,
                     start_at=_next_local(1, 10), hours=3, status='confirmed',
                     message='New geyser line to the back cottage.',
                     provider_responded_at=now - timedelta(hours=5))
    _event(c1, 'requested', 'confirmed', themba.id, 'provider')
    _notify_pair(c1, 'booking_confirmed', to_provider=False)
    c2 = _mk_booking(service=braiding, requester=b4,
                     start_at=_next_local(4, 11), hours=2, status='confirmed',
                     message='Medium box braids, shoulder length.',
                     provider_responded_at=now - timedelta(hours=20))
    _event(c2, 'requested', 'confirmed', sarah.id, 'provider')
    _notify_pair(c2, 'booking_confirmed', to_provider=False)

    # declined (1) — past.
    d1 = _mk_booking(service=bathroom, requester=b5,
                     start_at=_past_local(6, 8), hours=8, status='declined',
                     message='Full re-do of the main bathroom.',
                     provider_responded_at=_past_local(7, 15),
                     cancel_reason='Booked solid that week — try the following Monday.')
    _event(d1, 'requested', 'declined', themba.id, 'provider',
           note='Booked solid that week — try the following Monday.')
    _notify_pair(d1, 'booking_declined', to_provider=False)

    # cancelled (1) — past, cancelled by requester before start.
    x1 = _mk_booking(service=styling, requester=b1,
                     start_at=_past_local(9, 15), hours=1, status='cancelled',
                     message='Quick blow-dry before dinner.',
                     provider_responded_at=_past_local(10, 9),
                     cancelled_by='requester',
                     cancel_reason='Plans changed — sorry!')
    _event(x1, 'requested', 'confirmed', sarah.id, 'provider')
    _event(x1, 'confirmed', 'cancelled', b1.id, 'requester',
           note='Plans changed — sorry!')
    _notify_pair(x1, 'booking_cancelled', to_provider=True)

    # expired (1) — past, provider never responded.
    e1 = _mk_booking(service=tap_repair, requester=b2,
                     start_at=_past_local(14, 11), hours=1, status='expired',
                     message='Outside tap dripping.',
                     expires_at=_past_local(14, 11))
    _event(e1, 'requested', 'expired', None, 'system')
    _notify_pair(e1, 'booking_expired', to_provider=False)

    # completed (3) — past 30 days; feeds the ranking (Themba 2, Sarah 1).
    comp_specs = [
        (pipe_install, b3, _past_local(5, 9), 2, 'Bathroom basin re-pipe.'),
        (tap_repair, b4, _past_local(18, 10), 1, 'Garden tap replacement.'),
        (braiding, b5, _past_local(8, 12), 2, 'Cornrows with beads.'),
    ]
    for s_, buyer_, start_, hrs_, msg_ in comp_specs:
        cb = _mk_booking(service=s_, requester=buyer_, start_at=start_,
                         hours=hrs_, status='completed', message=msg_,
                         provider_responded_at=start_ - timedelta(days=1),
                         completed_at=start_ + timedelta(hours=hrs_, minutes=30))
        _event(cb, 'requested', 'confirmed', s_.provider_user_id, 'provider')
        _event(cb, 'confirmed', 'completed', None, 'system')
        _notify_pair(cb, 'booking_completed', to_provider=True)
        _notify_pair(cb, 'booking_completed', to_provider=False)

    # no_show (1) — past.
    n1 = _mk_booking(service=styling, requester=b2,
                     start_at=_past_local(4, 16), hours=1, status='no_show',
                     message='Updo for graduation photos.',
                     provider_responded_at=_past_local(5, 10), no_show=True)
    _event(n1, 'requested', 'confirmed', sarah.id, 'provider')
    _event(n1, 'confirmed', 'no_show', sarah.id, 'provider')
    _notify_pair(n1, 'booking_no_show', to_provider=False)

    # disputed — OPEN (1): requester contests a no-show flag.
    do_ = _mk_booking(service=tap_repair, requester=b5,
                      start_at=_past_local(3, 10), hours=1, status='disputed',
                      message='Bathroom tap will not close fully.',
                      provider_responded_at=_past_local(4, 12), no_show=True)
    _event(do_, 'requested', 'confirmed', themba.id, 'provider')
    _event(do_, 'confirmed', 'no_show', themba.id, 'provider')
    disp_open = BookingDispute(
        booking_id=do_.id, raised_by=b5.id, raised_by_role='requester',
        reason='I was home the whole morning — the provider never arrived.',
        status='open')
    db.session.add(disp_open)
    db.session.flush()
    do_.dispute_id = disp_open.id
    _event(do_, 'no_show', 'disputed', b5.id, 'requester',
           note='I was home the whole morning — the provider never arrived.')
    _notify_pair(do_, 'dispute_raised', to_provider=True)

    # disputed — RESOLVED (1): late cancel contested, admin resolved → cancelled.
    admin = User.query.filter_by(email='admin@zimhub.local').first()
    dr_ = _mk_booking(service=braiding, requester=b3,
                      start_at=_past_local(16, 13), hours=2, status='cancelled',
                      message='Braids before holiday travel.',
                      provider_responded_at=_past_local(17, 9),
                      cancelled_by='admin',
                      cancel_reason='Resolved by dispute admin.')
    _event(dr_, 'requested', 'confirmed', sarah.id, 'provider')
    _event(dr_, 'confirmed', 'disputed', sarah.id, 'provider',
           note='Client cancelled at the door after I had travelled out.')
    disp_resolved = BookingDispute(
        booking_id=dr_.id, raised_by=sarah.id, raised_by_role='provider',
        reason='Client cancelled at the door after I had travelled out.',
        status='resolved', resolution='cancelled',
        resolution_note='Cancellation upheld; both parties notified. No money moves on-platform.',
        resolved_by=admin.id if admin else None,
        resolved_at=_past_local(15, 10))
    db.session.add(disp_resolved)
    db.session.flush()
    dr_.dispute_id = disp_resolved.id
    _event(dr_, 'disputed', 'cancelled', admin.id if admin else None, 'admin',
           note='Cancellation upheld.')
    _notify_pair(dr_, 'dispute_resolved', to_provider=True)
    _notify_pair(dr_, 'dispute_resolved', to_provider=False)

    db.session.commit()

    mock_added = _mock_count() - mock_count_before

    # ---------------- CLI output (per spec §7.1) ----------------
    print('''
✓ Stage 4 seed complete (on top of Stages 1, 2, 3).

Providers:
  provider1@zimhub.local — Themba Plumbing (Plumber) — 3 services
  provider2@zimhub.local — Sarah Mobile Hair (Hairdresser) — 3 services

Services by pricing unit:
  flat:     2
  per_hour: 2
  per_day:  1
  per_km:   1

Recurring availability seeded.
One-off blocks seeded: 4

Bookings by state:
  requested:  2
  confirmed:  2
  declined:   1
  cancelled:  1 (+1 dispute-resolved cancellation)
  expired:    1
  completed:  3
  no_show:    1
  disputed (open):     1
  disputed (resolved): 1
''')
    print(f'Mock messages added: {mock_added}')
    print()
    print('Walk docs/STAGE_4_ACCEPTANCE.md to verify.')


def _mock_count():
    from app.models import MockMessage
    return db.session.query(MockMessage).count()


def _notify_pair(booking, kind, *, to_provider: bool):
    """Seed an in-app notification + mock WhatsApp via the host seam, mirroring
    what the live state machine emits."""
    target = booking.provider if to_provider else booking.requester
    titles = {
        'booking_requested': 'New booking request',
        'booking_confirmed': 'Booking confirmed',
        'booking_declined': 'Booking declined',
        'booking_cancelled': 'Booking cancelled',
        'booking_expired': 'Booking request expired',
        'booking_completed': 'Booking completed',
        'booking_no_show': 'Marked as no-show',
        'dispute_raised': 'Booking dispute raised',
        'dispute_resolved': 'Booking dispute resolved',
    }
    title = titles.get(kind, kind)
    body = f'{title} — booking {str(booking.id)[:8]}.'
    host.notify(target.id, kind, title, body,
                metadata={'booking_id': str(booking.id)})
    host.send('whatsapp', target.phone, f'{title} — {body}',
              payload={'booking_id': str(booking.id), 'kind': kind})
