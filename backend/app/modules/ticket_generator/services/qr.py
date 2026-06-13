"""QR signing / verification per TICKET_GENERATOR_SPEC.md §7.

Payload format:
    <ticket_uuid>.<random_24_url_safe_chars>.<hmac_sha256_first_32_hex_chars>

    signature = HMAC-SHA256(secret=QR_HMAC_SECRET,
                            msg="<ticket_uuid>.<random>")[:32]

Constant-time comparison on verify; signature failure → invalid.
"""
import hmac
import hashlib
import secrets
import string

from app.services import host


# 24 chars of URL-safe entropy (alphanumeric + a few symbols would also be fine,
# but for QR readability we stick to [A-Za-z0-9]).
_URL_SAFE_CHARS = string.ascii_letters + string.digits


def _secret() -> bytes:
    s = host.config('QR_HMAC_SECRET', None)
    if not s:
        # In dev/seed before host config is set; fall back to a stable default.
        # Production deploy MUST set QR_HMAC_SECRET via config.
        s = 'zimhub-dev-qr-secret-change-me'
    return s.encode('utf-8') if isinstance(s, str) else s


def _make_random() -> str:
    return ''.join(secrets.choice(_URL_SAFE_CHARS) for _ in range(24))


def _sign_msg(msg: str) -> str:
    return hmac.new(_secret(), msg.encode('utf-8'), hashlib.sha256).hexdigest()[:32]


def sign_payload(ticket_uuid: str) -> str:
    """Mint a fresh QR payload for a ticket id (string UUID)."""
    rnd = _make_random()
    msg = f"{ticket_uuid}.{rnd}"
    sig = _sign_msg(msg)
    return f"{msg}.{sig}"


def verify_payload(payload: str):
    """Return (ticket_uuid, ok). ok=False on any parse/signature failure.

    Constant-time signature compare.
    """
    if not payload or not isinstance(payload, str):
        return None, False
    parts = payload.split('.')
    if len(parts) != 3:
        return None, False
    tid, rnd, sig = parts
    if not tid or not rnd or not sig:
        return None, False
    expected = _sign_msg(f"{tid}.{rnd}")
    if not hmac.compare_digest(expected, sig):
        return None, False
    return tid, True
