"""Stage 1 seed — per spec §7.

Creates:
  - 1 super admin
  - 5 buyers
  - 5 pending seller signup requests across the 4 categories
  - 3 already-approved sellers (salesman, promoter, provider) + profile shells
  - ~10 notifications across users (mix of read/unread)
  - ~5 mock messages
"""
from datetime import datetime, timezone, timedelta

from extensions import db
from app.models import (
    User,
    SellerSignupRequest,
    SalesmanProfile,
    PromoterProfile,
    ProviderProfile,
    Notification,
    MockMessage,
)
from app.utils.passwords import hash_password
from app.utils.slugify import slugify_unique


def utcnow():
    return datetime.now(timezone.utc)


def run():
    # Idempotency: if the super admin already exists, assume seeded.
    if User.query.filter_by(email='admin@zimhub.local').first():
        print('• Seed appears to have already run (admin@zimhub.local exists). Skipping.')
        return

    # ---------------- Super admin ----------------
    admin = User(
        email='admin@zimhub.local',
        phone='+263772000001',
        password_hash=hash_password('Admin123!'),
        name='Mqhelisi Sibindi',
        suburb='Hillside',
        city='Bulawayo',
        is_buyer=True,
        is_super_admin=True,
        password_reset_required=False,
    )
    db.session.add(admin)

    # ---------------- Buyers ----------------
    buyer_suburbs = ['Hillside', 'Suburbs', 'Pumula', 'Cowdray Park', 'Mahatshula']
    buyer_names = [
        'Nomvula Dube',
        'Tendai Moyo',
        'Sibusiso Ncube',
        'Rumbidzai Sibanda',
        'Bongani Khumalo',
    ]
    buyers = []
    for i, (name, suburb) in enumerate(zip(buyer_names, buyer_suburbs), start=1):
        b = User(
            email=f'buyer{i}@zimhub.local',
            phone=f'+26377200010{i}',
            password_hash=hash_password('Buyer123!'),
            name=name,
            suburb=suburb,
            city='Bulawayo',
            is_buyer=True,
        )
        db.session.add(b)
        buyers.append(b)

    # ---------------- Approved sellers ----------------
    # Salesman
    salesman_user = User(
        email='salesman1@zimhub.local',
        phone='+263772000201',
        password_hash=hash_password('Seller123!'),
        name="Mthuli Ndlovu",
        suburb='Hillside',
        city='Bulawayo',
        is_buyer=True,
        is_salesman=True,
        password_reset_required=False,
    )
    db.session.add(salesman_user)
    db.session.flush()
    salesman_profile = SalesmanProfile(
        user_id=salesman_user.id,
        shop_name="Mthuli's Phone Hub",
        shop_slug=slugify_unique(
            "Mthuli's Phone Hub",
            exists_fn=lambda s: db.session.query(SalesmanProfile.user_id).filter_by(shop_slug=s).first() is not None,
        ),
        bio='Latest smartphones, accessories, and screen repairs in Hillside.',
        pickup_delivery_policy='Same-day pickup in Bulawayo CBD; nationwide courier on request.',
        default_currency='USD',
    )
    db.session.add(salesman_profile)

    # Promoter
    promoter_user = User(
        email='promoter1@zimhub.local',
        phone='+263772000202',
        password_hash=hash_password('Seller123!'),
        name='Sibusiso Mguni',
        suburb='Suburbs',
        city='Bulawayo',
        is_buyer=True,
        is_promoter=True,
        password_reset_required=False,
    )
    db.session.add(promoter_user)
    db.session.flush()
    promoter_profile = PromoterProfile(
        user_id=promoter_user.id,
        organisation_name='Bulawayo Live',
        bio='Live music nights and cultural festivals in Bulawayo.',
        default_currency='USD',
    )
    db.session.add(promoter_profile)

    # Provider
    provider_user = User(
        email='provider1@zimhub.local',
        phone='+263772000203',
        password_hash=hash_password('Seller123!'),
        name='Themba Nyathi',
        suburb='Pumula',
        city='Bulawayo',
        is_buyer=True,
        is_provider=True,
        password_reset_required=False,
    )
    db.session.add(provider_user)
    db.session.flush()
    provider_profile = ProviderProfile(
        user_id=provider_user.id,
        trade='Plumber',
        bio='Twelve years of residential and small-commercial plumbing in Bulawayo.',
        suburbs_served=['Hillside', 'Suburbs', 'Pumula', 'Cowdray Park', 'Bulawayo CBD'],
        default_currency='USD',
        timezone='Africa/Harare',
    )
    db.session.add(provider_profile)

    db.session.flush()

    # ---------------- Pending signup requests ----------------
    pending_requests = [
        SellerSignupRequest(
            category='salesman',
            full_name='Nokuthula Sithole',
            business_name='Thula Threads',
            email='nokuthula.sithole@example.com',
            phone='+263772100011',
            suburb='Khumalo',
            pitch='Affordable Afrocentric clothing for working women, made in Bulawayo. Looking to reach a wider audience.',
            category_payload={
                'shop_name': 'Thula Threads',
                'primary_category': 'Womenswear',
                'sample_products': 'Ankara skirts, kitenge blazers, handmade accessories',
                'pickup_delivery_preference': 'Pickup in Khumalo + nationwide courier',
            },
            status='pending',
            created_at=utcnow() - timedelta(hours=3),
        ),
        SellerSignupRequest(
            category='salesman',
            full_name='Tatenda Chigumba',
            business_name='Phone Accessories ZW',
            email='tatenda.chigumba@example.com',
            phone='+263772100012',
            suburb='Bulawayo CBD',
            pitch='Imported phone accessories — cases, chargers, earphones — sold from a CBD shop.',
            category_payload={
                'shop_name': 'Phone Accessories ZW',
                'primary_category': 'Electronics & accessories',
                'sample_products': 'Phone cases, fast chargers, Bluetooth earphones',
                'pickup_delivery_preference': 'CBD walk-in + Bulawayo delivery',
            },
            status='pending',
            created_at=utcnow() - timedelta(hours=10),
        ),
        SellerSignupRequest(
            category='promoter',
            full_name='Lindiwe Phiri',
            business_name='Riverwalk Events',
            email='lindiwe@riverwalkevents.example',
            phone='+263772100013',
            suburb='Riverside',
            pitch='Run mid-sized music nights at Riverwalk. Two events per month, average 300 attendees.',
            category_payload={
                'organisation_name': 'Riverwalk Events',
                'past_events': '"Sundowner Sessions" (monthly, 18 months running)',
                'sample_poster_url': 'https://example.com/riverwalk-poster.jpg',
                'event_categories': ['Live music', 'Outdoor', 'Sundowners'],
            },
            status='pending',
            created_at=utcnow() - timedelta(days=1, hours=2),
        ),
        SellerSignupRequest(
            category='provider',
            full_name='Joseph Mhlanga',
            business_name=None,
            email='joseph.mhlanga@example.com',
            phone='+263772100014',
            suburb='North End',
            pitch='Electrician — 15 years of experience, certified, primarily residential rewiring and solar installs.',
            category_payload={
                'trade': 'Electrician',
                'years_experience': 15,
                'service_areas': ['Hillside', 'North End', 'Khumalo', 'Suburbs'],
                'pricing_unit_preference': 'per_job',
            },
            status='pending',
            created_at=utcnow() - timedelta(days=2),
        ),
        SellerSignupRequest(
            category='creator',
            full_name='Zenzo Mathema',
            business_name='Zenzo Sound',
            email='zenzo@zenzosound.example',
            phone='+263772100015',
            suburb='Famona',
            pitch='Independent musician releasing afro-soul singles. Want a single home for my music, links and merch.',
            category_payload={
                'creator_types': ['musician', 'producer'],
                'sample_work_urls': ['https://soundcloud.example/zenzo', 'https://instagram.example/zenzo.sound'],
                'discipline_tags': ['afro-soul', 'jazz', 'bulawayo'],
            },
            status='pending',
            created_at=utcnow() - timedelta(hours=6),
        ),
    ]
    for req in pending_requests:
        db.session.add(req)

    db.session.flush()

    # ---------------- Notifications ----------------
    # 4 for super admin (new_signup_request, one per pending application from the
    # first four — leave one without an admin notif so we have variety).
    for r in pending_requests[:4]:
        db.session.add(Notification(
            user_id=admin.id,
            kind='new_signup_request',
            title=f'New {r.category} application',
            body=f"{r.full_name} ({r.email}) applied to sell as {r.category}.",
            metadata_json={
                'request_id': str(r.id),
                'category': r.category,
                'email': r.email,
            },
            read_at=utcnow() - timedelta(hours=1) if r is pending_requests[0] else None,
            created_at=r.created_at,
        ))

    # 3 notifications for buyer1 — welcoming and informational.
    db.session.add(Notification(
        user_id=buyers[0].id,
        kind='welcome',
        title='Welcome to ZimHub',
        body='Thanks for joining. The Shop, Events, Services, and Creators sections open over the coming weeks.',
        metadata_json={},
        read_at=utcnow() - timedelta(days=1),
        created_at=utcnow() - timedelta(days=2),
    ))
    db.session.add(Notification(
        user_id=buyers[0].id,
        kind='announcement',
        title='Shop launches in Stage 2',
        body='The Shop section opens soon — you\'ll be able to buy directly from Bulawayo sellers.',
        metadata_json={},
        read_at=None,
        created_at=utcnow() - timedelta(hours=12),
    ))
    db.session.add(Notification(
        user_id=buyers[0].id,
        kind='announcement',
        title='Events tickets coming soon',
        body='QR-coded tickets for Bulawayo events are on the way.',
        metadata_json={},
        read_at=None,
        created_at=utcnow() - timedelta(hours=4),
    ))

    # 2 notifications for already-approved sellers (welcome / approval echo).
    db.session.add(Notification(
        user_id=salesman_user.id,
        kind='seller_application_approved',
        title='Approved: Salesman application',
        body="Welcome to ZimHub. Your application to sell as a salesman has been approved.",
        metadata_json={'category': 'salesman'},
        read_at=utcnow() - timedelta(days=1),
        created_at=utcnow() - timedelta(days=3),
    ))
    db.session.add(Notification(
        user_id=promoter_user.id,
        kind='seller_application_approved',
        title='Approved: Promoter application',
        body="Welcome to ZimHub. Your application to sell as a promoter has been approved.",
        metadata_json={'category': 'promoter'},
        read_at=None,
        created_at=utcnow() - timedelta(days=2),
    ))

    # ---------------- Mock messages ----------------
    # 3 approval emails for the three approved sellers, 1 rejection email, 1 password reset email.
    login_url = 'http://localhost:5173/login'

    db.session.add(MockMessage(
        channel='email',
        recipient=salesman_user.email,
        subject='ZimHub — your seller application is approved',
        body=(
            f"Hi {salesman_user.name},\n\n"
            f"Welcome to ZimHub. Your application to sell as a salesman has been approved.\n\n"
            f"Sign in here: {login_url}\n"
            f"Email: {salesman_user.email}\n"
            f"Temporary password: (already changed)\n"
        ),
        payload={'template': 'seller_application_approved', 'category': 'salesman'},
        created_at=utcnow() - timedelta(days=3),
    ))
    db.session.add(MockMessage(
        channel='email',
        recipient=promoter_user.email,
        subject='ZimHub — your seller application is approved',
        body=f"Hi {promoter_user.name},\n\nYour promoter application has been approved.",
        payload={'template': 'seller_application_approved', 'category': 'promoter'},
        created_at=utcnow() - timedelta(days=2),
    ))
    db.session.add(MockMessage(
        channel='email',
        recipient=provider_user.email,
        subject='ZimHub — your seller application is approved',
        body=f"Hi {provider_user.name},\n\nYour provider application has been approved.",
        payload={'template': 'seller_application_approved', 'category': 'provider'},
        created_at=utcnow() - timedelta(days=1),
    ))
    db.session.add(MockMessage(
        channel='email',
        recipient='rejected.applicant@example.com',
        subject='ZimHub — your seller application',
        body=(
            'Hi Banele,\n\nThanks for applying to sell on ZimHub as a salesman.\n'
            "Unfortunately we can't take it forward at this time.\n\n"
            'Reason: Pitch did not clearly describe the products being sold.\n'
        ),
        payload={'template': 'seller_application_rejected', 'category': 'salesman',
                 'reason': 'Pitch did not clearly describe the products being sold.'},
        created_at=utcnow() - timedelta(hours=20),
    ))
    db.session.add(MockMessage(
        channel='email',
        recipient=buyers[1].email,
        subject='ZimHub — password reset',
        body=f"Hi {buyers[1].name},\n\nSomeone asked to reset the password on your ZimHub account.\nIgnore this if it wasn't you.\n",
        payload={'template': 'password_reset'},
        created_at=utcnow() - timedelta(hours=5),
    ))

    db.session.commit()

    print('')
    print('✓ Stage 1 seed complete.')
    print('')
    print('Super admin')
    print('  admin@zimhub.local / Admin123!')
    print('')
    print('Buyers (5)')
    print('  buyer1@zimhub.local … buyer5@zimhub.local / Buyer123!')
    print('')
    print('Approved sellers (3)')
    print("  salesman1@zimhub.local — Mthuli's Phone Hub (salesman)")
    print('  promoter1@zimhub.local — Bulawayo Live (promoter)')
    print('  provider1@zimhub.local — Themba Plumbing (provider)')
    print('  All passwords: Seller123!')
    print('')
    print('Pending signup requests: 5')
    print('Notifications seeded: 10')
    print('Mock messages seeded: 5')
    print('')
