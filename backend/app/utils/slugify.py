"""Custom slugify — per spec §11.

lowercase, hyphenate, strip non-alphanumeric; resolve collisions with -2, -3, …
"""
import re


def slugify(text: str) -> str:
    if not text:
        return 'untitled'
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", '', s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", '-', s)
    s = s.strip('-')
    return s or 'untitled'


def slugify_unique(text: str, exists_fn) -> str:
    """Returns a slug guaranteed unique against exists_fn(candidate) → bool."""
    base = slugify(text)
    candidate = base
    i = 2
    while exists_fn(candidate):
        candidate = f"{base}-{i}"
        i += 1
    return candidate
