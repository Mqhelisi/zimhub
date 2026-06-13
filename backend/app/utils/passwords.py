"""Password hashing + temp password generation."""
import bcrypt
import secrets
import string


# Per spec §5.1 — bcrypt work factor 12.
BCRYPT_ROUNDS = 12


def hash_password(plaintext: str) -> str:
    if not isinstance(plaintext, str):
        raise ValueError('Password must be a string')
    return bcrypt.hashpw(plaintext.encode('utf-8'), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode('utf-8')


def verify_password(plaintext: str, hashed: str) -> bool:
    if not plaintext or not hashed:
        return False
    try:
        return bcrypt.checkpw(plaintext.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def validate_password_rules(password: str):
    """Per spec §5.1: min 8 chars, ≥1 digit. Raises ValueError on failure."""
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not any(c.isdigit() for c in password):
        raise ValueError('Password must contain at least one digit')


# Chars chosen to avoid visual ambiguity (no 0/O/1/l/I).
_TEMP_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'


def generate_temp_password(length: int = 12) -> str:
    """Generate a memorable-enough temp password that satisfies the rules."""
    # Ensure at least one digit by picking digits separately.
    pool = _TEMP_CHARS
    digits = '23456789'
    pwd = [secrets.choice(digits)]
    pwd += [secrets.choice(pool) for _ in range(length - 1)]
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)
