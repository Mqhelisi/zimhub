"""Stage 3 seed — per STAGE_3_SPEC.md §7.

Runs AFTER stage2_seed (cumulative). Adds:
  - Enriched promoter1 profile (photo / bio)
  - 4 events for promoter1:
      Event A: ticketed, upcoming (14d), 2 ticket types
      Event B: ticketed, past 7d (1 type, scanned tickets seeded)
      Event C: flyer, upcoming (21d), with external_link + WhatsApp text
      Event D: flyer, past 5d
  - Gatemen: 2 for Event A, 1 for Event B (PIN 1234 all)
  - Ticket Purchases in every PurchaseInterface state
  - Tickets in every TG-defined state (valid, used, voided)
  - mock_messages corresponding to deliveries

Idempotent: skips if Event A's title already exists for the promoter.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging

from extensions import db
from app.models import User, PromoterProfile, Notification, MockMessage
from app.modules.ticket_generator.models import (
    Event, TicketType, Ticket, Gateman, Checkin,
)
from app.modules.ticket_generator.services.qr import sign_payload
from app.modules.purchase_interface.models import (
    Purchase, PurchaseEvent, PurchaseDispute,
)
from app.utils.passwords import hash_password


log = logging.getLogger('zimhub.seed.stage3')


def utcnow():
    return datetime.now(timezone.utc)


def _img(seed, w=1200, h=800):
    return f'https://picsum.photos/seed/{seed}/{w}/{h}'


# ---------------------------------------------------------------------------
# Promoter enrichment
# ---------------------------------------------------------------------------
def _enrich_promoter(promoter):
    p = promoter.promoter_profile
    if not p:
        p = PromoterProfile(user_id=promoter.id, default_currency='USD')
        db.session.add(p)
        db.session.flush()
    if not p.organisation_name:
        p.organisation_name = 'Bulawayo Live'
    if not p.bio:
        p.bio = ('Bulawayo-based events promoter running live music, '
                 'cultural nights, and sundowner sessions across the city.')
    if not p.photo_url:
        p.photo_url = _img('bulawayo-live-promoter-photo', 400, 400)
    return p


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
def _create_events(promoter, now):
    """Returns dict of events by code (A/B/C/D)."""
    events = {}

    # Event A — ticketed upcoming
    ev_a = Event(
        promoter_id=promoter.id,
        title='Amapiano Sundowner — Riverwalk',
        description=('A relaxed amapiano sundowner with a rotating DJ lineup '
                     'on the Riverwalk lawn. Bring a jacket for the late set.'),
        category='Music',
        start_at=now + timedelta(days=14, hours=17),
        end_at=now + timedelta(days=14, hours=23),
        location='Riverwalk Lawn, Suburbs, Bulawayo',
        poster_url=_img('event-a-amapiano-sundowner', 1200, 800),
        poster_thumb_url=_img('event-a-amapiano-sundowner', 400, 266),
        color_scheme='#c026d3,#facc15',
        status='active', mode='ticketed',
    )
    db.session.add(ev_a)
    db.session.flush()

    # 2 ticket types
    tt_a_general = TicketType(
        event_id=ev_a.id, name='General',
        description='Standard entry to the lawn.',
        price_usd=Decimal('5.00'), quantity_total=200,
    )
    tt_a_vip = TicketType(
        event_id=ev_a.id, name='VIP',
        description='Reserved seating area + welcome drink.',
        price_usd=Decimal('15.00'), quantity_total=40,
    )
    db.session.add_all([tt_a_general, tt_a_vip])
    db.session.flush()

    # Event B — ticketed past (with scanned tickets)
    ev_b = Event(
        promoter_id=promoter.id,
        title='Gospel Festival — Stanley Square',
        description=('An evening of choirs, soloists, and praise teams from '
                     'Bulawayo and Harare. Family-friendly, doors at 4pm.'),
        category='Church',
        start_at=now - timedelta(days=7, hours=4),
        end_at=now - timedelta(days=7, hours=-3),  # 7d ago, 7h event
        location='Stanley Square, Bulawayo CBD',
        poster_url=_img('event-b-gospel-festival', 1200, 800),
        poster_thumb_url=_img('event-b-gospel-festival', 400, 266),
        color_scheme='#86198f,#facc15',
        status='active', mode='ticketed',
    )
    db.session.add(ev_b)
    db.session.flush()
    tt_b_entry = TicketType(
        event_id=ev_b.id, name='Entry',
        description='General entry.',
        price_usd=Decimal('3.00'), quantity_total=300,
    )
    db.session.add(tt_b_entry)
    db.session.flush()

    # Event C — flyer upcoming
    ev_c = Event(
        promoter_id=promoter.id,
        title='Comedy Night at the Theatre — Tickets at the door',
        description=('Local comedians + headline from Harare. Tickets at the '
                     'door only; tap WhatsApp to reserve a table.'),
        category='Comedy',
        start_at=now + timedelta(days=21, hours=19),
        end_at=now + timedelta(days=21, hours=23),
        location='Bulawayo Theatre, Main Street',
        poster_url=_img('event-c-comedy-night', 1200, 800),
        poster_thumb_url=_img('event-c-comedy-night', 400, 266),
        color_scheme='#c026d3,#facc15',
        status='active', mode='flyer',
        external_link='https://example.com/comedy-night-rsvp',
        whatsapp_deep_link_text=(
            'Hi Bulawayo Live, I want to reserve a table for the comedy night at '
            'the Theatre. How many seats are left?'
        ),
    )
    db.session.add(ev_c)

    # Event D — flyer past
    ev_d = Event(
        promoter_id=promoter.id,
        title='Heritage Day Cultural Market',
        description=('Crafters, food, and dance troupes celebrating Heritage Day '
                     'across the city park.'),
        category='Festival',
        start_at=now - timedelta(days=5, hours=9),
        end_at=now - timedelta(days=5, hours=-9),  # all day, 5d ago
        location='Centenary Park, Bulawayo',
        poster_url=_img('event-d-heritage-market', 1200, 800),
        poster_thumb_url=_img('event-d-heritage-market', 400, 266),
        color_scheme='#86198f,#facc15',
        status='active', mode='flyer',
    )
    db.session.add(ev_d)

    db.session.flush()
    events.update({
        'A': ev_a, 'B': ev_b, 'C': ev_c, 'D': ev_d,
        'A_general': tt_a_general, 'A_vip': tt_a_vip, 'B_entry': tt_b_entry,
    })
    return events


# ---------------------------------------------------------------------------
# Gatemen
# ---------------------------------------------------------------------------
def _create_gatemen(promoter, events, now):
    pin_hash = hash_password('1234')
    gatemen = {}
    # Event A — 2 gatemen
    gm_a1 = Gateman(
        event_id=events['A'].id, name='Sipho Ncube',
        phone='+263772100001', pin_hash=pin_hash,
        locked_until=events['A'].end_at + timedelta(hours=24),
        created_by=promoter.id,
    )
    gm_a2 = Gateman(
        event_id=events['A'].id, name='Themba Dube',
        phone='+263772100002', pin_hash=pin_hash,
        locked_until=events['A'].end_at + timedelta(hours=24),
        created_by=promoter.id,
    )
    # Event B — 1 gateman (locked window already past, but seed needs them
    # for the scanned-tickets attribution; locked_until is just informational).
    gm_b1 = Gateman(
        event_id=events['B'].id, name='Lindiwe Moyo',
        phone='+263772100003', pin_hash=pin_hash,
        locked_until=events['B'].end_at + timedelta(hours=24),
        created_by=promoter.id,
    )
    db.session.add_all([gm_a1, gm_a2, gm_b1])
    db.session.flush()
    gatemen.update({'A1': gm_a1, 'A2': gm_a2, 'B1': gm_b1})
    return gatemen


# ---------------------------------------------------------------------------
# Purchase factory — every Purchase state + tickets per state per spec
# ---------------------------------------------------------------------------
def _log_pevent(purchase, frm, to, actor_id, role, note, when):
    db.session.add(PurchaseEvent(
        purchase_id=purchase.id, from_status=frm, to_status=to,
        actor_id=actor_id, actor_role=role, note=note, created_at=when,
    ))


def _make_purchase(*, state, promoter, buyer, ticket_type, quantity,
                   attendee_names, created_at, payment_ref=None,
                   dispute_reason=None, dispute_resolution=None,
                   dispute_resolver=None, hold_hours=24):
    """Insert a Purchase row in the requested state, with all related rows."""
    unit_price = Decimal(str(ticket_type.price_usd))
    total = (unit_price * Decimal(quantity)).quantize(Decimal('0.01'))

    p = Purchase(
        listing_type='event_ticket',
        listing_id=ticket_type.id,
        seller_id=promoter.id,
        buyer_id=buyer.id,
        quantity=quantity,
        unit_price_usd=unit_price,
        total_usd=total,
        currency='USD',
        status='awaiting_payment',
        domain_payload={
            'ticket_type_id': str(ticket_type.id),
            'event_id': str(ticket_type.event_id),
            'attendee_names': attendee_names,
            'buyer_name_at_purchase': buyer.name,
            'buyer_phone_at_purchase': buyer.phone,
            'unit_price_usd_at_checkout': str(unit_price),
        },
        hold_expires_at=created_at + timedelta(hours=hold_hours),
        created_at=created_at,
        updated_at=created_at,
    )
    db.session.add(p)
    db.session.flush()
    _log_pevent(p, None, 'awaiting_payment', buyer.id, 'buyer',
                'Purchase initiated.', created_at)

    if state == 'awaiting_payment':
        # Hold the inventory.
        ticket_type.quantity_held = (ticket_type.quantity_held or 0) + quantity
        return p, []

    seller_at = created_at + timedelta(hours=3)

    if state in ('awaiting_buyer_confirmation', 'completed',
                 'disputed_open', 'disputed_resolved_refunded'):
        # Mint tickets (status='valid' regardless of buyer-confirmation).
        ticket_type.quantity_sold = (ticket_type.quantity_sold or 0) + quantity
        p.seller_confirmed_at = seller_at
        p.payment_ref = payment_ref or 'ECOCASH-EV-' + str(p.id)[:6].upper()
        p.fulfillment_refs = {'ticket_count': quantity}
        minted = []
        for name in attendee_names:
            t = Ticket(
                ticket_type_id=ticket_type.id,
                purchase_id=p.id,
                attendee_name=name,
                source='online',
                price_usd=unit_price,
                payment_ref=p.payment_ref,
                qr_code='seed-placeholder',
                status='valid',
                created_at=seller_at,
            )
            db.session.add(t)
            db.session.flush()
            t.qr_code = sign_payload(str(t.id))
            minted.append(t)
        _log_pevent(p, 'awaiting_payment', 'awaiting_buyer_confirmation',
                    promoter.id, 'seller',
                    'Payment confirmed; goods delivered.', seller_at)

        if state == 'awaiting_buyer_confirmation':
            p.status = 'awaiting_buyer_confirmation'
            p.auto_complete_at = seller_at + timedelta(hours=72)
            p.updated_at = seller_at
            return p, minted

        if state == 'completed':
            buyer_at = seller_at + timedelta(hours=18)
            p.status = 'completed'
            p.buyer_confirmed_at = buyer_at
            p.completed_at = buyer_at
            _log_pevent(p, 'awaiting_buyer_confirmation', 'completed',
                        buyer.id, 'buyer', 'Receipt confirmed.', buyer_at)
            p.updated_at = buyer_at
            return p, minted

        if state == 'disputed_open':
            dispute_at = seller_at + timedelta(hours=14)
            p.status = 'disputed'
            p.auto_complete_at = None
            dispute = PurchaseDispute(
                purchase_id=p.id, raised_by=buyer.id, raised_by_role='buyer',
                reason=dispute_reason or 'Promoter still hasn\'t emailed me the tickets.',
                status='open', created_at=dispute_at,
            )
            db.session.add(dispute)
            db.session.flush()
            p.dispute_id = dispute.id
            _log_pevent(p, 'awaiting_buyer_confirmation', 'disputed',
                        buyer.id, 'buyer',
                        f'Dispute raised: {dispute.reason[:140]}', dispute_at)
            p.updated_at = dispute_at
            return p, minted

        if state == 'disputed_resolved_refunded':
            dispute_at = seller_at + timedelta(hours=12)
            resolved_at = dispute_at + timedelta(hours=10)
            dispute = PurchaseDispute(
                purchase_id=p.id, raised_by=buyer.id, raised_by_role='buyer',
                reason=dispute_reason or 'Event line-up changed last minute.',
                status='resolved', resolution='refunded',
                resolution_note='Verified with both parties via WhatsApp. '
                                'Refund agreed.',
                resolved_by=dispute_resolver.id if dispute_resolver else None,
                created_at=dispute_at, resolved_at=resolved_at,
            )
            db.session.add(dispute)
            db.session.flush()
            p.dispute_id = dispute.id
            p.status = 'refunded'
            # Reverse inventory.
            ticket_type.quantity_sold = max(0, (ticket_type.quantity_sold or 0) - quantity)
            # Void the minted tickets.
            for t in minted:
                t.status = 'voided'
            _log_pevent(p, 'awaiting_buyer_confirmation', 'disputed',
                        buyer.id, 'buyer',
                        f'Dispute raised: {dispute.reason[:140]}', dispute_at)
            _log_pevent(p, 'disputed', 'refunded',
                        dispute_resolver.id if dispute_resolver else None,
                        'admin',
                        'Dispute resolved as refunded.', resolved_at)
            p.updated_at = resolved_at
            return p, minted

    if state == 'cancelled':
        cancelled_at = created_at + timedelta(hours=2)
        p.status = 'cancelled'
        _log_pevent(p, 'awaiting_payment', 'cancelled',
                    buyer.id, 'buyer', 'Changed my mind.', cancelled_at)
        p.updated_at = cancelled_at
        return p, []

    if state == 'expired':
        p.status = 'expired'
        p.hold_expires_at = created_at + timedelta(hours=hold_hours)
        expired_at = p.hold_expires_at + timedelta(minutes=5)
        _log_pevent(p, 'awaiting_payment', 'expired',
                    None, 'system', 'Hold window elapsed.', expired_at)
        p.updated_at = expired_at
        return p, []

    raise ValueError(f'Unknown state {state}')


# ---------------------------------------------------------------------------
# Walk-in / scanned ticket factories
# ---------------------------------------------------------------------------
def _seed_walk_in_ticket(ticket_type, *, attendee, walk_in_name, walk_in_phone,
                        payment_ref, when):
    """Direct-mint a walk-in ticket (no Purchase row)."""
    t = Ticket(
        ticket_type_id=ticket_type.id, purchase_id=None,
        attendee_name=attendee, source='walk_in',
        walk_in_name=walk_in_name, walk_in_phone=walk_in_phone,
        price_usd=ticket_type.price_usd,
        payment_ref=payment_ref,
        qr_code='walk-in-placeholder', status='valid',
        created_at=when,
    )
    db.session.add(t)
    db.session.flush()
    t.qr_code = sign_payload(str(t.id))
    ticket_type.quantity_sold = (ticket_type.quantity_sold or 0) + 1
    return t


def _seed_comp_ticket(ticket_type, *, attendee, when):
    t = Ticket(
        ticket_type_id=ticket_type.id, purchase_id=None,
        attendee_name=attendee, source='comp',
        price_usd=Decimal('0.00'), payment_ref='COMP',
        qr_code='comp-placeholder', status='valid', created_at=when,
    )
    db.session.add(t)
    db.session.flush()
    t.qr_code = sign_payload(str(t.id))
    ticket_type.quantity_sold = (ticket_type.quantity_sold or 0) + 1
    return t


def _mark_used(ticket, gateman, when, device_id='seed-device'):
    ticket.status = 'used'
    ticket.checked_in_at = when
    ticket.checked_in_by = gateman.id
    ticket.checked_in_device = device_id
    db.session.add(Checkin(
        ticket_id=ticket.id, gateman_id=gateman.id,
        device_id=device_id, scanned_at=when, synced_at=when,
        result='success',
    ))
    gateman.scan_count = (gateman.scan_count or 0) + 1
    gateman.last_seen_at = when


# ---------------------------------------------------------------------------
# Notifications + mock_messages
# ---------------------------------------------------------------------------
def _seed_notification(*, user_id, kind, title, body, when, metadata=None, read=False):
    db.session.add(Notification(
        user_id=user_id, kind=kind, title=title, body=body,
        metadata_json=metadata or {},
        read_at=when if read else None, created_at=when,
    ))


def _seed_whatsapp_mock(*, recipient, body, when, template, purchase_id=None):
    db.session.add(MockMessage(
        channel='whatsapp', recipient=recipient, subject=None, body=body,
        payload={'template': template,
                 **({'purchase_id': str(purchase_id)} if purchase_id else {})},
        created_at=when,
    ))


def _seed_sms_mock(*, recipient, body, when, template, purchase_id=None):
    db.session.add(MockMessage(
        channel='sms', recipient=recipient, subject=None, body=body,
        payload={'template': template,
                 **({'purchase_id': str(purchase_id)} if purchase_id else {})},
        created_at=when,
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run():
    now = utcnow()

    promoter = User.query.filter_by(email='promoter1@zimhub.local').first()
    if not promoter:
        print('• Stage 1 promoter missing — run Stage 1 seed first.')
        return

    admin = User.query.filter_by(email='admin@zimhub.local').first()
    buyers = [User.query.filter_by(email=f'buyer{i}@zimhub.local').first()
              for i in range(1, 6)]
    if not all(buyers):
        print('• Stage 1 buyers missing — run Stage 1 seed first.')
        return

    # Idempotency check.
    existing_a = (Event.query
                  .filter(Event.promoter_id == promoter.id,
                          Event.title == 'Amapiano Sundowner — Riverwalk')
                  .first())
    if existing_a is not None:
        print('• Stage 3 seed appears to have already run (Event A exists). Skipping.')
        return

    _enrich_promoter(promoter)
    events = _create_events(promoter, now)
    gatemen = _create_gatemen(promoter, events, now)

    msg_count = 0
    purchase_state_counts = {
        'awaiting_payment': 0, 'awaiting_buyer_confirmation': 0,
        'completed': 0, 'cancelled': 0, 'expired': 0,
        'disputed (open)': 0, 'disputed (resolved)': 0,
    }
    ticket_state_counts = {'valid': 0, 'used': 0, 'voided': 0}

    # ----------------------------------------------------------------
    # Ticket Purchases — every state, against Event A (upcoming).
    # ----------------------------------------------------------------
    plan = [
        # awaiting_payment ×2
        dict(state='awaiting_payment', buyer=buyers[0],
             tt=events['A_general'], quantity=2,
             attendees=['Nomvula Dube', '+1 friend'],
             hours_ago=3),
        dict(state='awaiting_payment', buyer=buyers[1],
             tt=events['A_vip'], quantity=1,
             attendees=['Tendai Moyo'],
             hours_ago=1),

        # awaiting_buyer_confirmation ×1 (payment landed, awaiting receipt)
        dict(state='awaiting_buyer_confirmation', buyer=buyers[2],
             tt=events['A_general'], quantity=3,
             attendees=['Sibusiso Ncube', 'Sis Lulu', 'Cousin Khaya'],
             hours_ago=20),

        # completed ×4
        dict(state='completed', buyer=buyers[0],
             tt=events['A_general'], quantity=1,
             attendees=['Nomvula Dube'], hours_ago=72),
        dict(state='completed', buyer=buyers[3],
             tt=events['A_general'], quantity=2,
             attendees=['Rumbidzai Sibanda', 'Plus 1'], hours_ago=140),
        dict(state='completed', buyer=buyers[4],
             tt=events['A_vip'], quantity=1,
             attendees=['Bongani Khumalo'], hours_ago=200),
        dict(state='completed', buyer=buyers[1],
             tt=events['B_entry'], quantity=2,
             attendees=['Tendai Moyo', '+1 friend'], hours_ago=24 * 9),

        # cancelled ×1
        dict(state='cancelled', buyer=buyers[2],
             tt=events['A_general'], quantity=1,
             attendees=['Sibusiso Ncube'], hours_ago=30),

        # expired ×1
        dict(state='expired', buyer=buyers[3],
             tt=events['A_vip'], quantity=1,
             attendees=['Rumbidzai Sibanda'], hours_ago=50),

        # disputed (open) ×1 — open dispute against Event A
        dict(state='disputed_open', buyer=buyers[4],
             tt=events['A_general'], quantity=2,
             attendees=['Bongani Khumalo', 'Plus 1'],
             hours_ago=40,
             dispute_reason='Promoter confirmed payment but tickets never arrived in my inbox.'),

        # disputed (resolved → refunded) ×1
        dict(state='disputed_resolved_refunded', buyer=buyers[0],
             tt=events['A_general'], quantity=1,
             attendees=['Nomvula Dube'],
             hours_ago=110,
             dispute_resolver=admin),
    ]

    completed_minted = []  # used to mark some as 'used' for past-event scanning

    for cfg in plan:
        created_at = now - timedelta(hours=cfg['hours_ago'])
        state = cfg['state']
        bucket_state = ('disputed (open)' if state == 'disputed_open' else
                        'disputed (resolved)' if state == 'disputed_resolved_refunded' else
                        state)
        purchase, tickets = _make_purchase(
            state=state, promoter=promoter, buyer=cfg['buyer'],
            ticket_type=cfg['tt'], quantity=cfg['quantity'],
            attendee_names=cfg['attendees'], created_at=created_at,
            dispute_reason=cfg.get('dispute_reason'),
            dispute_resolver=cfg.get('dispute_resolver'),
        )
        purchase_state_counts[bucket_state] = purchase_state_counts.get(bucket_state, 0) + 1
        for t in tickets:
            ticket_state_counts[t.status] = ticket_state_counts.get(t.status, 0) + 1
        # Notifications + mock messages
        label = f"{cfg['tt'].event.title} — {cfg['tt'].name}"
        _seed_notification(
            user_id=promoter.id, kind='purchase_initiated',
            title=f"New ticket purchase: {label}",
            body=f"A buyer committed to {cfg['quantity']} ticket(s) "
                 f"for {label}.",
            when=created_at,
            metadata={'purchase_id': str(purchase.id)},
            read=state not in ('awaiting_payment',),
        )
        _seed_notification(
            user_id=cfg['buyer'].id, kind='purchase_initiated',
            title=f"Tickets reserved: {label}",
            body=f"You committed to buy {cfg['quantity']} ticket(s) for {label}. "
                 f"Total ${purchase.total_usd}. Coordinate over WhatsApp.",
            when=created_at, metadata={'purchase_id': str(purchase.id)},
            read=state not in ('awaiting_payment',),
        )
        _seed_whatsapp_mock(
            recipient=promoter.phone,
            body=(f"ZimHub: Hi {promoter.name.split(' ')[0]}, this is about "
                  f"my purchase: {label}. Total ${purchase.total_usd}. "
                  f"Ref: {str(purchase.id)[:8]}"),
            when=created_at, template='ticket_purchase_initiated_b2s',
            purchase_id=purchase.id,
        )
        msg_count += 1

        if state in ('awaiting_buyer_confirmation', 'completed',
                     'disputed_open', 'disputed_resolved_refunded'):
            # event_ticket_issued + payment_confirmed notif + delivery mocks
            seller_at = created_at + timedelta(hours=3)
            _seed_notification(
                user_id=cfg['buyer'].id, kind='event_ticket_issued',
                title=f"Tickets issued: {cfg['tt'].event.title}",
                body=f"{cfg['quantity']} ticket(s) for {cfg['tt'].event.title} "
                     f"— {cfg['tt'].name}. Open My Tickets for QR codes.",
                when=seller_at, metadata={
                    'purchase_id': str(purchase.id),
                    'event_id': str(cfg['tt'].event.id),
                },
                read=state == 'completed',
            )
            for ch in ('sms', 'whatsapp'):
                seeder = _seed_sms_mock if ch == 'sms' else _seed_whatsapp_mock
                seeder(
                    recipient=cfg['buyer'].phone,
                    body=(f"ZimHub: {cfg['quantity']} ticket(s) for "
                          f"{cfg['tt'].event.title} ({cfg['tt'].name}) are now "
                          f"valid and scannable. Open My Tickets to view your QRs."),
                    when=seller_at,
                    template='event_ticket_issued',
                    purchase_id=purchase.id,
                )
                msg_count += 1
            if state == 'completed':
                completed_minted.append((cfg, purchase, tickets))

    # ----------------------------------------------------------------
    # Event B — past-event tickets, mostly scanned ('used')
    # The completed Event B Purchase above already minted 2 valid tickets.
    # Mark them used + add a couple of seed-direct walk-in tickets and
    # mark them used too, to show the attendees-list with scan history.
    # ----------------------------------------------------------------
    # Find the completed Event B purchase tickets:
    event_b_completed = [(cfg, p, ts) for (cfg, p, ts) in completed_minted
                         if cfg['tt'].event.id == events['B'].id]
    scan_when = events['B'].start_at + timedelta(hours=1)
    used_count = 0
    for cfg, p, ts in event_b_completed:
        for t in ts:
            _mark_used(t, gatemen['B1'], scan_when + timedelta(minutes=used_count))
            ticket_state_counts['valid'] -= 1
            ticket_state_counts['used'] += 1
            used_count += 1

    # Add 3 walk-in tickets to Event B, mark all as used (real-world door sales).
    for i, (name, phone) in enumerate([
        ('Wisdom Chari', '+263772100201'),
        ('Faith Mhlanga', '+263772100202'),
        ('Junior Maboko', '+263772100203'),
    ]):
        t = _seed_walk_in_ticket(
            events['B_entry'], attendee=name,
            walk_in_name=name, walk_in_phone=phone,
            payment_ref=f'WALKIN:CASH-{i+1:02d}',
            when=events['B'].start_at - timedelta(minutes=30 - i),
        )
        _mark_used(t, gatemen['B1'],
                   events['B'].start_at + timedelta(minutes=5 + i))
        ticket_state_counts['used'] += 1

    # ----------------------------------------------------------------
    # Direct-seed additional valid + voided tickets on Event A so the
    # spec's count is met (≥ 8 valid, ≥ 5 used, ≥ 2 voided).
    # ----------------------------------------------------------------
    # Voided: 2 extra (admin-initiated test scenario).
    for i, name in enumerate(['Tested-Void-1', 'Tested-Void-2']):
        t = _seed_comp_ticket(events['A_general'], attendee=name, when=now - timedelta(days=2))
        t.status = 'voided'
        ticket_state_counts['voided'] += 1

    # Top up valid count if under 8 — add comp tickets to Event A.
    while ticket_state_counts['valid'] < 8:
        idx = ticket_state_counts['valid']
        _seed_comp_ticket(events['A_general'], attendee=f'VIP Comp #{idx + 1}',
                          when=now - timedelta(days=1))
        ticket_state_counts['valid'] += 1

    # Top up used count if under 5 — mark one more Event A ticket used.
    # (For demo purposes; uses gateman A1)
    if ticket_state_counts['used'] < 5:
        # Mint a comp + immediately scan it (rehearsal scan)
        rehearsal = _seed_comp_ticket(events['A_general'],
                                       attendee='Rehearsal scan',
                                       when=now - timedelta(hours=2))
        _mark_used(rehearsal, gatemen['A1'], now - timedelta(hours=1))
        ticket_state_counts['used'] += 1

    db.session.commit()

    # ---------------- Report ----------------
    print('')
    print('✓ Stage 3 seed complete (on top of Stages 1 and 2).')
    print('')
    print('Promoter:')
    print(f"  {promoter.email} — Bulawayo Live")
    print('')
    print('Events (4):')
    print('  Event A — ticketed, upcoming in 14 days     (General $5, VIP $15)')
    print('  Event B — ticketed, past 7 days ago         (Entry $3; scanned tickets seeded)')
    print('  Event C — flyer, upcoming in 21 days        (external link + WhatsApp greeting)')
    print('  Event D — flyer, past 5 days ago')
    print('')
    print('Gatemen (PIN 1234 for all):')
    print('  +263772100001  Sipho Ncube     (Event A)')
    print('  +263772100002  Themba Dube     (Event A)')
    print('  +263772100003  Lindiwe Moyo    (Event B)')
    print('')
    print('Ticket Purchases by state:')
    order = ['awaiting_payment', 'awaiting_buyer_confirmation', 'completed',
             'cancelled', 'expired', 'disputed (open)', 'disputed (resolved)']
    for k in order:
        n = purchase_state_counts.get(k, 0)
        if n:
            print(f'  {k:32s} {n}')
    print('')
    print('Tickets by state:')
    for k in ('valid', 'used', 'voided'):
        print(f'  {k:8s} {ticket_state_counts.get(k, 0)}')
    print('')
    print(f'Mock messages added: {msg_count}')
    print('')
    print('Walk docs/STAGE_3_ACCEPTANCE.md to verify all 50 cumulative steps.')
