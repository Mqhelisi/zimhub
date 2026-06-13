"""Auth service — encapsulates user creation, login, password reset logic.
Routes call into this rather than touching models directly.
"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from extensions import db
from app.models import User, PasswordResetToken
from app.utils.passwords import (
    hash_password,
    verify_password,
    validate_password_rules,
)
from app.utils.phone import normalise_phone


def create_buyer(email: str, phone: str, password: str, name: str,
                 suburb: str = None, city: str = 'Bulawayo') -> User:
    """Create a Buyer user. Raises ValueError on rule violations.

    The route layer is responsible for catching ValueError and translating to a
    400 response with the right error code.
    """
    email = (email or '').strip().lower()
    if not email or '@' not in email:
        raise ValueError('A valid email is required')
    name = (name or '').strip()
    if not name:
        raise ValueError('Name is required')

    validate_password_rules(password)
    normalised_phone = normalise_phone(phone)

    existing = User.query.filter_by(email=email).first()
    if existing:
        raise EmailTakenError('Email already in use')

    user = User(
        email=email,
        phone=normalised_phone,
        password_hash=hash_password(password),
        name=name,
        suburb=(suburb or None),
        city=city or 'Bulawayo',
        is_buyer=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def authenticate(email: str, password: str) -> User | None:
    if not email or not password:
        return None
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    if user.status == 'suspended':
        raise AccountSuspendedError('Your account has been suspended.')
    return user


def change_password(user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        # Allow passing the temp password as the current one on the forced-change flow.
        raise ValueError('Current password is incorrect')
    validate_password_rules(new_password)
    user.password_hash = hash_password(new_password)
    user.password_reset_required = False


def issue_password_reset_token(user: User) -> PasswordResetToken:
    token = PasswordResetToken(
        token=uuid4(),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(token)
    db.session.flush()
    return token


def consume_password_reset_token(token_value: str, new_password: str) -> User:
    try:
        from uuid import UUID
        token_uuid = UUID(str(token_value))
    except (ValueError, TypeError):
        raise ValueError('Invalid reset token')

    token = db.session.get(PasswordResetToken, token_uuid)
    if not token:
        raise ValueError('Invalid reset token')
    if token.used_at is not None:
        raise ValueError('This reset link has already been used')
    if token.expires_at < datetime.now(timezone.utc):
        raise ValueError('This reset link has expired')

    user = db.session.get(User, token.user_id)
    if not user:
        raise ValueError('Invalid reset token')

    validate_password_rules(new_password)
    user.password_hash = hash_password(new_password)
    user.password_reset_required = False
    token.used_at = datetime.now(timezone.utc)
    return user


# --- Custom error types so route layer can map to the correct response code. ---

class EmailTakenError(Exception):
    pass


class AccountSuspendedError(Exception):
    pass
