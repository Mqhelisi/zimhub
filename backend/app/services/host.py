"""ZimHub host services — THE contract Stages 2–5 will consume.

Per spec §5.4. Every route in Stage 1 routes notifications and dispatches through
this module rather than touching the DB or transport details directly. This proves
the seam works and gives Stage 2 a stable surface to plug PurchaseInterface into.

Public surface (keep small and stable):
    current_user()
    can_sell(user, listing_type) -> bool
    is_provider(user) -> bool
    is_dispute_admin(user) -> bool
    notify(user_id, kind, title, body, metadata=None) -> Notification
    whatsapp_link(phone, text) -> str
    send(channel, recipient, body, subject=None, payload=None) -> MockMessage
    config(key, default=None)

Plus the LISTING_TYPE_TO_CAPABILITY registry which Stage 2's product module
will append to (e.g. 'product' -> 'is_salesman').
"""
import logging
from urllib.parse import quote_plus

from flask import current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from extensions import db
from app.models import User, Notification, MockMessage
from config import SYSTEM_CONFIG


log = logging.getLogger('zimhub.host')


# ---------------------------------------------------------------------------
# Capability registry — Stage 2's product module will register 'product' here.
# Stage 1 leaves it empty.
# ---------------------------------------------------------------------------
LISTING_TYPE_TO_CAPABILITY: dict = {
    'product': 'is_salesman',                      # Stage 2
    # Stage 5: event_ticket is ANY-OF — a value may be a single flag string OR
    # a tuple of flags (the seller passes if they hold ANY one of them). This is
    # the one host-level can_sell change in Stage 5 (§5.3): creators sell tickets
    # to their OWN events without holding the full Promoter capability. The
    # TicketGenerator module registers 'is_promoter' at boot; creator_platform
    # re-asserts the tuple LAST in create_app(), so the final value is the tuple.
    'event_ticket': ('is_promoter', 'is_creator'),  # Stage 3 (+ Stage 5 any-of)
    # 'service_slot' is deliberately NOT here — BookingInterface uses its own
    # parallel BOOKABLE_TYPE_TO_CAPABILITY registry below.
}


def register_listing_type(listing_type: str, capability_flag) -> None:
    """Extend the registry. capability_flag may be a single flag string OR a
    tuple/list of flags (any-of). Used by later stages without touching this
    file's logic."""
    LISTING_TYPE_TO_CAPABILITY[listing_type] = capability_flag


# ---------------------------------------------------------------------------
# Stage 4 — BookingInterface's PARALLEL capability registry. BookingInterface
# is NOT a PurchaseInterface listing type; the two systems never share state,
# so 'service_provider' is deliberately NOT added to LISTING_TYPE_TO_CAPABILITY.
# ---------------------------------------------------------------------------
BOOKABLE_TYPE_TO_CAPABILITY: dict = {
    'service_provider': 'is_provider',   # Stage 4
}


def register_bookable_type(bookable_type: str, capability_flag: str) -> None:
    """BI analogue of register_listing_type — extends the BI registry only."""
    BOOKABLE_TYPE_TO_CAPABILITY[bookable_type] = capability_flag


def can_book_as_provider(user, bookable_type: str) -> bool:
    """BI analogue of can_sell — may this user act as the PROVIDER side of
    this bookable_type (accept/decline/availability)?"""
    if not user:
        return False
    flag = BOOKABLE_TYPE_TO_CAPABILITY.get(bookable_type)
    if not flag:
        return False
    return bool(getattr(user, flag, False))


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------
def current_user():
    """Return the User from the JWT cookie, or None if anonymous.

    Caller decides whether anonymity is acceptable; this function does not raise.
    """
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        return None
    if not user_id:
        return None
    return db.session.get(User, user_id)


# ---------------------------------------------------------------------------
# Capability checks
# ---------------------------------------------------------------------------
def can_sell(user, listing_type: str) -> bool:
    """True iff the user holds the capability mapped to this listing_type.

    Stage 1: registry is empty → always False (no modules registered yet).
    Stage 2+: 'product' → 'is_salesman', etc.
    Stage 5: a mapped value may be a tuple/list of flags (ANY-OF). For
    'event_ticket' the value is ('is_promoter', 'is_creator') — a promoter OR a
    creator may sell event tickets; a pure buyer holds neither and is rejected.
    """
    if not user:
        return False
    flag = LISTING_TYPE_TO_CAPABILITY.get(listing_type)
    if not flag:
        return False
    if isinstance(flag, (tuple, list)):
        return any(bool(getattr(user, f, False)) for f in flag)
    return bool(getattr(user, flag, False))


def is_provider(user) -> bool:
    return bool(user and user.is_provider)


def is_dispute_admin(user) -> bool:
    return bool(user and user.is_super_admin)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
def notify(user_id, kind: str, title: str, body: str, metadata: dict = None) -> Notification:
    """Insert a notification row. Returns the persisted Notification.

    Caller is responsible for db.session.commit() if running inside a unit-of-work.
    For convenience we flush so the row gets an id immediately.
    """
    n = Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        metadata_json=metadata or {},
    )
    db.session.add(n)
    db.session.flush()
    log.info('[NOTIFY] user=%s kind=%s title=%r', user_id, kind, title)
    return n


# ---------------------------------------------------------------------------
# Mock transports — logged AND persisted to mock_messages.
# ---------------------------------------------------------------------------
def whatsapp_link(phone: str, text: str) -> str:
    """Return https://wa.me/<digits>?text=<urlencoded>. Strips + and non-digits."""
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    return f"https://wa.me/{digits}?text={quote_plus(text or '')}"


def send(channel: str, recipient: str, body: str, subject: str = None, payload: dict = None) -> MockMessage:
    """Send a message via mock transport.

    channel ∈ {'whatsapp', 'sms', 'email'}.
    Logs to stdout AND writes a mock_messages row. No real provider is called.
    """
    if channel not in ('whatsapp', 'sms', 'email'):
        raise ValueError(f'Unknown channel: {channel}')

    msg = MockMessage(
        channel=channel,
        recipient=recipient,
        subject=subject,
        body=body,
        payload=payload or {},
    )
    db.session.add(msg)
    db.session.flush()

    log.info(
        '[MOCK MESSAGE] channel=%s recipient=%s subject=%r body_preview=%r',
        channel,
        recipient,
        subject,
        (body or '')[:120],
    )
    return msg


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def config(key: str, default=None):
    """Read a runtime config key. Defaults documented in config.SYSTEM_CONFIG."""
    return SYSTEM_CONFIG.get(key, default)


def set_config(key: str, value):
    """Mutator used by /api/super/config PUT."""
    SYSTEM_CONFIG[key] = value
    return SYSTEM_CONFIG.get(key)


def all_config() -> dict:
    return dict(SYSTEM_CONFIG)
