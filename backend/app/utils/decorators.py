"""Auth + role decorators. Per spec §5.4 — capabilities are read live from the
DB, NOT from the JWT, so flag changes take effect immediately.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from extensions import db
from app.models import User


def _err(code: str, message: str, status: int):
    return jsonify({'error': code, 'message': message}), status


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception:
            return _err('unauthenticated', 'You must be signed in.', 401)
        user_id = get_jwt_identity()
        user = db.session.get(User, user_id)
        if not user:
            return _err('unauthenticated', 'Your session is no longer valid.', 401)
        if user.status == 'suspended':
            return _err('forbidden', 'This account is suspended.', 403)
        return fn(user, *args, **kwargs)
    return wrapper


def require_role(role: str):
    """role ∈ {'super_admin', ...}. Reads the live capability from DB."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                return _err('unauthenticated', 'You must be signed in.', 401)
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)
            if not user:
                return _err('unauthenticated', 'Your session is no longer valid.', 401)
            if user.status == 'suspended':
                return _err('forbidden', 'This account is suspended.', 403)
            flag_attr = f'is_{role}'
            if not getattr(user, flag_attr, False):
                return _err('forbidden', 'You do not have access to this resource.', 403)
            return fn(user, *args, **kwargs)
        return wrapper
    return deco
