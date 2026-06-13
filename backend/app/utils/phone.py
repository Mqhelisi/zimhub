"""Phone normalisation for Zimbabwe.

Per spec §5.1: accept +263XXXXXXXXX or 07XXXXXXXX, store as E.164.
"""
import re


def normalise_phone(raw: str) -> str:
    """Normalise a Zimbabwean phone number to E.164 (+263…).

    Accepts:
        +263772123456 → +263772123456
        263772123456  → +263772123456
        0772123456    → +263772123456
        0 77 212 3456 → +263772123456 (whitespace stripped)
    Raises ValueError on anything we can't recognise.
    """
    if raw is None:
        raise ValueError('Phone is required')
    s = re.sub(r'[\s\-\(\)]', '', str(raw))
    if not s:
        raise ValueError('Phone is required')
    if s.startswith('+263') and len(s) == 13 and s[1:].isdigit():
        return s
    if s.startswith('263') and len(s) == 12 and s.isdigit():
        return '+' + s
    if s.startswith('0') and len(s) == 10 and s.isdigit():
        return '+263' + s[1:]
    # Permissive fallback: any +<digits> with 10–15 digits total — pass through.
    if s.startswith('+') and s[1:].isdigit() and 10 <= len(s) - 1 <= 15:
        return s
    raise ValueError(f'Could not normalise phone: {raw}')


def is_valid_phone(raw: str) -> bool:
    try:
        normalise_phone(raw)
        return True
    except ValueError:
        return False
