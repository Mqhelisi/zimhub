"""Auth endpoints — per spec §5.1.

JWT in httpOnly cookies. CORS configured for credentials in app factory.
"""
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
)

from extensions import db
from app.models import User
from app.services import auth_service
from app.services.mock_transport import dispatch_password_reset_email
from app.services.notification_service import notify_password_reset_requested
from app.utils.decorators import require_auth
from app.utils.errors import (
    error_response,
    validation_failed,
    email_taken,
    unauthenticated,
)


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _build_auth_response(user: User, status: int = 200):
    token = create_access_token(identity=str(user.id))
    resp = make_response(jsonify({'user': user.to_dict()}), status)
    set_access_cookies(resp, token)
    return resp


@auth_bp.post('/signup')
def signup():
    data = request.get_json(silent=True) or {}
    try:
        user = auth_service.create_buyer(
            email=data.get('email'),
            phone=data.get('phone'),
            password=data.get('password'),
            name=data.get('name'),
            suburb=data.get('suburb'),
            city=data.get('city') or 'Bulawayo',
        )
    except auth_service.EmailTakenError:
        return email_taken()
    except ValueError as e:
        return validation_failed(str(e))

    db.session.commit()
    return _build_auth_response(user, status=201)


@auth_bp.post('/login')
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return validation_failed('Email and password are required')

    try:
        user = auth_service.authenticate(email, password)
    except auth_service.AccountSuspendedError as e:
        return error_response('forbidden', str(e), 403)

    if not user:
        return unauthenticated('Invalid email or password.')

    return _build_auth_response(user)


@auth_bp.post('/logout')
def logout():
    # We don't require auth on logout — if there's no cookie, clearing it is a no-op.
    resp = make_response(jsonify({'ok': True}))
    unset_jwt_cookies(resp)
    return resp


@auth_bp.post('/password-reset/request')
def password_reset_request():
    """Always returns ok — don't reveal account existence (spec §5.1)."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()

    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            token = auth_service.issue_password_reset_token(user)
            dispatch_password_reset_email(
                recipient_email=user.email,
                full_name=user.name,
                token=token.token,
            )
            notify_password_reset_requested(user)
            db.session.commit()

    return jsonify({'ok': True})


@auth_bp.post('/password-reset/confirm')
def password_reset_confirm():
    data = request.get_json(silent=True) or {}
    token = data.get('token')
    new_password = data.get('new_password')
    if not token or not new_password:
        return validation_failed('Token and new_password are required')

    try:
        auth_service.consume_password_reset_token(token, new_password)
    except ValueError as e:
        return validation_failed(str(e))

    db.session.commit()
    return jsonify({'ok': True})


@auth_bp.post('/password-change')
@require_auth
def password_change(user: User):
    data = request.get_json(silent=True) or {}
    current = data.get('current_password')
    new = data.get('new_password')
    if not current or not new:
        return validation_failed('current_password and new_password are required')
    try:
        auth_service.change_password(user, current, new)
    except ValueError as e:
        return validation_failed(str(e))
    db.session.commit()
    return jsonify({'ok': True})


@auth_bp.get('/me')
@require_auth
def me(user: User):
    """Return the current user + capabilities + admin entries for the nav.

    admin_entries is a list of {key, label, route} entries the frontend uses to
    build the "switch admin" menu. Stage 1's seller admins are stubs that link
    to /super if super, otherwise to a Stage-2-pending placeholder.
    """
    entries = []
    if user.is_super_admin:
        entries.append({'key': 'super_admin', 'label': 'Super Admin', 'route': '/super'})
    # Buyer surface — Stage 2 adds the purchases inbox.
    entries.append({'key': 'buyer', 'label': 'My Account', 'route': '/'})
    if user.is_buyer:
        entries.append({'key': 'my_purchases', 'label': 'My purchases', 'route': '/my/purchases'})
        entries.append({'key': 'my_tickets', 'label': 'My tickets', 'route': '/my/tickets'})
        entries.append({'key': 'my_bookings', 'label': 'My bookings', 'route': '/my/bookings'})
    if user.is_salesman:
        entries.append({'key': 'salesman', 'label': 'Shop admin', 'route': '/salesman'})
    if user.is_promoter:
        entries.append({'key': 'promoter', 'label': 'Promoter admin', 'route': '/promoter'})
    if user.is_provider:
        entries.append({'key': 'provider', 'label': 'Provider admin', 'route': '/provider'})
    if user.is_creator:
        entries.append({'key': 'creator', 'label': 'Creator Studio', 'route': '/creator'})

    return jsonify({
        'user': user.to_dict(),
        'capabilities': user.capabilities_dict(),
        'admin_entries': entries,
    })
