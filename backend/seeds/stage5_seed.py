"""Stage 5 seed — per STAGE_5_SPEC.md §7. Runs AFTER stage4_seed (cumulative).

Brings the platform to a fully-populated, demonstrable V1 state across all four
sections. Adds:

  - 3 creators (approved):
      creator1 "Thandeka" (Musician)        — 3 tracks + 1 ticketed event (via TG)
      creator2 "Lens by Bongani" (Photographer) — 2 gallery collections
      creator3 "Nkosana Arts" (Musician + Visual Artist) — 2 tracks + 1 collection
  - 1 ticketed creator event via the TicketGenerator bridge, with seeded ticket
    Purchases (completed + awaiting) and tickets in valid/used states + a gateman.
  - 1 free/external creator event.
  - 1 pending `creator` signup request (live approve-flow demo).
  - mock_messages for the ticket deliveries.

Idempotent: skips if creator1 already exists.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging

from extensions import db
from app.models import (
    User, CreatorProfile, SellerSignupRequest, Notification, MockMessage,
)
from app.modules.creator_platform.models import (
    Track, GalleryCollection, GalleryItem, CreatorEvent, PlayEvent,
)
from app.modules.ticket_generator.models import (
    Event, TicketType, Ticket, Gateman, Checkin,
)
from app.modules.ticket_generator.services.qr import sign_payload
from app.modules.purchase_interface.models import Purchase, PurchaseEvent
from app.utils.passwords import hash_password

log = logging.getLogger('zimhub.seed.stage5')

SELLER_PW = 'Seller123!'


def utcnow():
    return datetime.now(timezone.utc)


def _img(seed, w=1200, h=800):
    return f'https://picsum.photos/seed/{seed}/{w}/{h}'


def _audio(name):
    # Relative to the API origin; the frontend resolves it against VITE_API_BASE_URL.
    return f'/local_uploads/seed/audio/{name}.mp3'


# ---------------------------------------------------------------------------
# User + profile helpers
# ---------------------------------------------------------------------------
def _ensure_creator_user(email, name, phone):
    u = User.query.filter_by(email=email).first()
    if u is None:
        u = User(
            email=email, phone=phone, password_hash=hash_password(SELLER_PW),
            name=name, suburb='Bulawayo', city='Bulawayo',
            is_buyer=True, is_creator=True, password_reset_required=False,
        )
        db.session.add(u)
        db.session.flush()
    else:
        u.is_creator = True
    return u


def _ensure_profile(user, *, display_name, slug, types, tags, accent, hero,
                    bio, social, external):
    p = user.creator_profile
    if p is None:
        p = CreatorProfile(user_id=user.id, display_name=display_name,
                           creator_slug=slug)
        db.session.add(p)
        db.session.flush()
    p.display_name = display_name
    p.creator_slug = slug
    p.creator_types = types
    p.discipline_tags = tags
    p.accent_color = accent
    p.hero_image_url = hero
    p.photo_url = _img(slug + '-avatar', 400, 400)
    p.bio = bio
    p.social_links = social
    p.external_links = external
    p.module_order = {'order': []}
    p.status = 'approved'
    return p


def _add_track(profile, *, title, audio_name, cover_seed, genre, position,
               featuring=None, album=None, plays=0):
    t = Track(
        creator_id=profile.user_id, title=title, featuring=featuring,
        album=album, genre=genre, cover_art_url=_img(cover_seed, 600, 600),
        audio_url=_audio(audio_name), duration_seconds=30,
        is_visible=True, play_count=plays, position=position,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _add_collection(profile, *, title, description, image_seeds, category):
    c = GalleryCollection(creator_id=profile.user_id, title=title,
                          description=description)
    db.session.add(c)
    db.session.flush()
    for i, seed in enumerate(image_seeds):
        db.session.add(GalleryItem(
            creator_id=profile.user_id, collection_id=c.id,
            title=f'{title} — {i + 1}', category=category,
            year_created=2025, image_url=_img(seed, 1200, 900), is_visible=True,
        ))
    db.session.flush()
    return c


# ---------------------------------------------------------------------------
# Ticket purchase + ticket seeding (mirrors stage3_seed shape, compact)
# ---------------------------------------------------------------------------
def _log_pevent(purchase, frm, to, actor_id, role, note, when):
    db.session.add(PurchaseEvent(
        purchase_id=purchase.id, from_status=frm, to_status=to,
        actor_id=actor_id, actor_role=role, note=note, created_at=when,
    ))


def _seed_ticket_purchase(*, creator, buyer, ticket_type, quantity,
                          attendee_names, created_at, state):
    """Seed a Purchase + tickets for a creator-owned TG event. Returns minted."""
    unit = Decimal(str(ticket_type.price_usd))
    total = (unit * Decimal(quantity)).quantize(Decimal('0.01'))
    p = Purchase(
        listing_type='event_ticket', listing_id=ticket_type.id,
        seller_id=creator.id, buyer_id=buyer.id, quantity=quantity,
        unit_price_usd=unit, total_usd=total, currency='USD',
        status='awaiting_payment',
        domain_payload={
            'ticket_type_id': str(ticket_type.id),
            'event_id': str(ticket_type.event_id),
            'attendee_names': attendee_names,
            'buyer_name_at_purchase': buyer.name,
            'buyer_phone_at_purchase': buyer.phone,
            'unit_price_usd_at_checkout': str(unit),
        },
        hold_expires_at=created_at + timedelta(hours=24),
        created_at=created_at, updated_at=created_at,
    )
    db.session.add(p)
    db.session.flush()
    _log_pevent(p, None, 'awaiting_payment', buyer.id, 'buyer',
                'Purchase initiated.', created_at)

    if state == 'awaiting_payment':
        ticket_type.quantity_held = (ticket_type.quantity_held or 0) + quantity
        return p, []

    seller_at = created_at + timedelta(hours=2)
    ticket_type.quantity_sold = (ticket_type.quantity_sold or 0) + quantity
    p.seller_confirmed_at = seller_at
    p.payment_ref = 'ECOCASH-CR-' + str(p.id)[:6].upper()
    p.fulfillment_refs = {'ticket_count': quantity}
    minted = []
    for name in attendee_names:
        t = Ticket(
            ticket_type_id=ticket_type.id, purchase_id=p.id, attendee_name=name,
            source='online', price_usd=unit, payment_ref=p.payment_ref,
            qr_code='seed-placeholder', status='valid', created_at=seller_at,
        )
        db.session.add(t)
        db.session.flush()
        t.qr_code = sign_payload(str(t.id))
        minted.append(t)
    _log_pevent(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                creator.id, 'seller', 'Payment confirmed; tickets issued.', seller_at)

    if state == 'awaiting_buyer_confirmation':
        p.status = 'awaiting_buyer_confirmation'
        p.auto_complete_at = seller_at + timedelta(hours=72)
        p.updated_at = seller_at
    elif state == 'completed':
        buyer_at = seller_at + timedelta(hours=10)
        p.status = 'completed'
        p.buyer_confirmed_at = buyer_at
        p.completed_at = buyer_at
        _log_pevent(p, 'awaiting_buyer_confirmation', 'completed',
                    buyer.id, 'buyer', 'Receipt confirmed.', buyer_at)
        p.updated_at = buyer_at

    # Mock delivery messages
    db.session.add(MockMessage(
        channel='whatsapp', recipient=buyer.phone,
        body=f'ZimHub: {quantity} ticket(s) issued for your creator event. View QR in My Tickets.',
        payload={'purchase_id': str(p.id)}, created_at=seller_at,
    ))
    return p, minted


def _mark_used(ticket, gateman, when):
    ticket.status = 'used'
    ticket.checked_in_at = when
    ticket.checked_in_by = gateman.id
    ticket.checked_in_device = 'seed-gate-device'
    db.session.add(Checkin(
        ticket_id=ticket.id, gateman_id=gateman.id, scanned_at=when,
        synced_at=when, device_id='seed-gate-device', result='success',
    ))
    gateman.scan_count = (gateman.scan_count or 0) + 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run():
    now = utcnow()

    if User.query.filter_by(email='creator1@zimhub.local').first():
        print('• Stage 5 seed already applied (creator1 exists). Skipping.')
        return

    # ---- Creator 1 — Thandeka (Musician) -------------------------------
    c1 = _ensure_creator_user('creator1@zimhub.local', 'Thandeka', '+263772400001')
    p1 = _ensure_profile(
        c1, display_name='Thandeka', slug='thandeka',
        types=['musician'], tags=['afro-soul', 'amapiano', 'live'],
        accent='#db2777', hero=_img('thandeka-hero', 1600, 600),
        bio='Bulawayo-born afro-soul vocalist blending amapiano warmth with '
            'Ndebele storytelling. Live shows across Matabeleland.',
        social={'instagram': 'https://instagram.com/thandeka',
                'whatsapp': '+263772400001'},
        external={'spotify': 'https://open.spotify.com/artist/thandeka',
                  'youtube': 'https://youtube.com/@thandeka'},
    )
    _add_track(p1, title='Golden Hour', audio_name='thandeka-golden-hour',
               cover_seed='golden-hour-cover', genre='Afro-soul', position=0, plays=142)
    _add_track(p1, title='City Lights', audio_name='thandeka-city-lights',
               cover_seed='city-lights-cover', genre='Amapiano', position=1,
               featuring='DJ Nkanyezi', plays=98)
    _add_track(p1, title='Homeland', audio_name='thandeka-homeland',
               cover_seed='homeland-cover', genre='Afro-soul', position=2,
               album='Roots', plays=61)

    # ---- Creator 2 — Lens by Bongani (Photographer) --------------------
    c2 = _ensure_creator_user('creator2@zimhub.local', 'Bongani Ncube', '+263772400002')
    p2 = _ensure_profile(
        c2, display_name='Lens by Bongani', slug='lens-by-bongani',
        types=['photographer'], tags=['portrait', 'street', 'documentary'],
        accent='#0891b2', hero=_img('bongani-hero', 1600, 600),
        bio='Documentary and portrait photographer capturing everyday Bulawayo '
            '— markets, music, and the people who make the city.',
        social={'instagram': 'https://instagram.com/lensbybongani'},
        external={'behance': 'https://behance.net/lensbybongani'},
    )
    _add_collection(p2, title='Streets of Bulawayo',
                    description='A walk through the city centre at golden hour.',
                    image_seeds=['byo-street-1', 'byo-street-2', 'byo-street-3', 'byo-street-4'],
                    category='photography')
    _add_collection(p2, title='Faces',
                    description='Portrait series of Bulawayo creatives.',
                    image_seeds=['byo-face-1', 'byo-face-2', 'byo-face-3'],
                    category='photography')

    # ---- Creator 3 — Nkosana Arts (Musician + Visual Artist) -----------
    c3 = _ensure_creator_user('creator3@zimhub.local', 'Nkosana Dube', '+263772400003')
    p3 = _ensure_profile(
        c3, display_name='Nkosana Arts', slug='nkosana-arts',
        types=['musician', 'visual_artist'], tags=['experimental', 'mixed-media'],
        accent='#7c3aed', hero=_img('nkosana-hero', 1600, 600),
        bio='Multi-disciplinary artist — sound and canvas. Experimental beats '
            'paired with mixed-media paintings rooted in Ndebele geometry.',
        social={'instagram': 'https://instagram.com/nkosana.arts'},
        external={'soundcloud': 'https://soundcloud.com/nkosana-arts'},
    )
    _add_track(p3, title='Umoya', audio_name='nkosana-umoya',
               cover_seed='umoya-cover', genre='Experimental', position=0, plays=37)
    _add_track(p3, title='Canvas', audio_name='nkosana-canvas',
               cover_seed='canvas-cover', genre='Experimental', position=1, plays=24)
    _add_collection(p3, title='Geometry of Home',
                    description='Mixed-media works on Ndebele pattern and place.',
                    image_seeds=['nkosana-art-1', 'nkosana-art-2', 'nkosana-art-3'],
                    category='painting')

    db.session.flush()

    # ---- Ticketed creator event (Thandeka) via the TG bridge -----------
    # Build a REAL TicketGenerator event owned by creator1 — proves the bridge.
    ev = Event(
        promoter_id=c1.id, title='Thandeka Live — Roots Tour',
        description='An intimate afro-soul evening with the full live band. '
                    'Limited seating at the Bulawayo Theatre.',
        category='Music',
        start_at=now + timedelta(days=10),
        end_at=now + timedelta(days=10, hours=4),
        location='Bulawayo Theatre, City Centre',
        poster_url=_img('thandeka-live-poster', 1200, 1500),
        poster_thumb_url=_img('thandeka-live-poster', 600, 750),
        status='active', mode='ticketed',
    )
    db.session.add(ev)
    db.session.flush()
    tt_general = TicketType(event_id=ev.id, name='General', price_usd=Decimal('10.00'),
                            quantity_total=120)
    tt_vip = TicketType(event_id=ev.id, name='VIP (front rows)', price_usd=Decimal('25.00'),
                        quantity_total=30)
    db.session.add_all([tt_general, tt_vip])
    db.session.flush()

    # Link a CreatorEvent row to the TG event (Mode A / host_ticketing).
    ce_ticketed = CreatorEvent(
        creator_id=c1.id, submitted_by=c1.id, title=ev.title,
        description=ev.description, event_date=ev.start_at,
        venue_name=ev.location, ticketing_mode='host_ticketing',
        host_event_id=ev.id, status='approved', poster_url=ev.poster_url,
    )
    db.session.add(ce_ticketed)

    # Gateman for the creator event (PIN 1234 — matches the other seeded gatemen).
    gm = Gateman(
        event_id=ev.id, name='Thandeka Door', phone='+263772400009',
        pin_hash=hash_password('1234'),
        locked_until=ev.end_at + timedelta(hours=24), created_by=c1.id,
    )
    db.session.add(gm)
    db.session.flush()

    # Seed ticket purchases against the creator event.
    buyer1 = User.query.filter_by(email='buyer1@zimhub.local').first()
    buyer2 = User.query.filter_by(email='buyer2@zimhub.local').first()

    minted_all = []
    if buyer1:
        _, m1 = _seed_ticket_purchase(
            creator=c1, buyer=buyer1, ticket_type=tt_general, quantity=2,
            attendee_names=['Buyer One', 'Plus One'],
            created_at=now - timedelta(days=2), state='completed')
        minted_all += m1
    if buyer2:
        _, m2 = _seed_ticket_purchase(
            creator=c1, buyer=buyer2, ticket_type=tt_vip, quantity=1,
            attendee_names=['Buyer Two'],
            created_at=now - timedelta(days=1), state='awaiting_buyer_confirmation')
        minted_all += m2
        # awaiting_payment one (held inventory)
        _seed_ticket_purchase(
            creator=c1, buyer=buyer2, ticket_type=tt_general, quantity=1,
            attendee_names=['Buyer Two Again'],
            created_at=now - timedelta(hours=6), state='awaiting_payment')

    # Mark one completed ticket as already used (scanned at the gate).
    if minted_all:
        _mark_used(minted_all[0], gm, now - timedelta(days=1, hours=20))

    # ---- Free / external creator event (Lens by Bongani) ---------------
    ce_free = CreatorEvent(
        creator_id=c2.id, submitted_by=c2.id,
        title='Gallery Opening — "Streets of Bulawayo"',
        description='Opening night of the Streets of Bulawayo photo series. '
                    'Free entry, RSVP appreciated.',
        event_date=now + timedelta(days=18),
        venue_name='Nest Gallery, Hillside',
        ticketing_mode='external', ticket_price='free',
        external_ticket_url='https://example.com/rsvp/streets-of-bulawayo',
        status='approved', poster_url=_img('gallery-opening-poster', 1200, 1500),
    )
    db.session.add(ce_free)

    # ---- Pending creator signup request (live approve-flow demo) -------
    existing_pending = (SellerSignupRequest.query
                        .filter_by(category='creator', status='pending').first())
    if not existing_pending:
        db.session.add(SellerSignupRequest(
            category='creator', full_name='Sipho Moyo',
            business_name='Sipho Sounds', email='sipho.creator@example.com',
            phone='+263772400010', suburb='Nketa', city='Bulawayo',
            pitch='Bulawayo producer and DJ wanting a home for my mixtapes and '
                  'to sell tickets to my monthly sundowner sessions.',
            category_payload={
                'creator_types': ['musician'],
                'discipline_tags': ['house', 'amapiano', 'dj'],
                'display_name': 'Sipho Sounds',
            },
            status='pending',
        ))

    db.session.commit()

    # Tallies
    track_count = Track.query.count()
    mock_added = MockMessage.query.filter(
        MockMessage.body.like('%creator event%')).count()

    print('\n✓ Stage 5 seed complete (on top of Stages 1–4). V1 platform fully populated.\n')
    print('Creators (3):')
    print('  creator1@zimhub.local — Thandeka (Musician) — 3 tracks, 1 ticketed event')
    print('  creator2@zimhub.local — Lens by Bongani (Photographer) — 2 collections')
    print('  creator3@zimhub.local — Nkosana Arts (Musician + Visual Artist) — 2 tracks, 1 collection')
    print('\nCreator events:')
    print('  Thandeka Live — Roots Tour (ticketed, via TicketGenerator) — in 10 days, tickets seeded')
    print('  Gallery Opening (free/external) — in 18 days')
    print('\nPending creator signup request: 1 (for live approve-flow demo)')
    print(f'\nMock messages added (ticket deliveries): {mock_added}')
    print('\nAll four sections are now live and seeded:')
    print('  Shop (Stage 2) · Events (Stage 3) · Services (Stage 4) · Creators (Stage 5)\n')
    print('Walk docs/STAGE_5_ACCEPTANCE.md to verify — this is the full V1 walkthrough.')
