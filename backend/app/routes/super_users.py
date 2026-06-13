"""Super admin user management — per spec §5.3."""
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, func

from extensions import db
from app.models import User
from app.routes.signup_requests import _ensure_profile_shell, CAPABILITY_FLAG_BY_CATEGORY
from app.services.mock_transport import dispatch_temp_password
from app.utils.decorators import require_role
from app.utils.errors import not_found, validation_failed, conflict
from app.utils.passwords import hash_password, generate_temp_password


super_users_bp = Blueprint('super_users', __name__, url_prefix='/api/super/users')


CAPABILITY_FIELDS = (
    'is_salesman',
    'is_promoter',
    'is_provider',
    'is_creator',
    'is_super_admin',
)

CATEGORY_BY_CAPABILITY = {v: k for k, v in CAPABILITY_FLAG_BY_CATEGORY.items()}


def _user_to_listing(u: User) -> dict:
    return {
        **u.to_dict(),
        'capability_pills': [k for k in CAPABILITY_FIELDS if getattr(u, k)],
    }


def _profile_snapshot(u: User) -> dict:
    return {
        'salesman': u.salesman_profile.to_dict() if u.salesman_profile else None,
        'promoter': u.promoter_profile.to_dict() if u.promoter_profile else None,
        'provider': u.provider_profile.to_dict() if u.provider_profile else None,
        'creator':  u.creator_profile.to_dict()  if u.creator_profile  else None,
    }


@super_users_bp.get('')
@require_role('super_admin')
def list_users(user: User):
    q = (request.args.get('q') or '').strip()
    capability = request.args.get('capability')
    status = request.args.get('status')
    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(max(int(request.args.get('page_size', 20)), 1), 100)
    except (ValueError, TypeError):
        page_size = 20

    query = User.query
    if q:
        like = f'%{q.lower()}%'
        query = query.filter(or_(
            func.lower(User.name).like(like),
            func.lower(User.email).like(like),
            User.phone.like(f'%{q}%'),
        ))
    if capability and capability in CAPABILITY_FIELDS + ('is_buyer',):
        query = query.filter(getattr(User, capability) == True)  # noqa: E712
    if status:
        query = query.filter(User.status == status)

    total = query.count()
    rows = (
        query.order_by(User.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )
    return jsonify({
        'users': [_user_to_listing(u) for u in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@super_users_bp.get('/<uuid:user_id>')
@require_role('super_admin')
def get_user(user: User, user_id):
    u = db.session.get(User, user_id)
    if not u:
        return not_found('User not found.')
    return jsonify({
        'user': u.to_dict(),
        'capabilities': u.capabilities_dict(),
        'profiles': _profile_snapshot(u),
    })


@super_users_bp.patch('/<uuid:user_id>/capabilities')
@require_role('super_admin')
def patch_capabilities(user: User, user_id):
    u = db.session.get(User, user_id)
    if not u:
        return not_found('User not found.')
    data = request.get_json(silent=True) or {}

    changed = False
    for field in CAPABILITY_FIELDS:
        if field in data:
            new_value = bool(data[field])
            if getattr(u, field) != new_value:
                setattr(u, field, new_value)
                changed = True
                # On enabling a seller capability, create the profile shell.
                # Disabling leaves the profile in place (soft-disable per §5.3).
                if new_value and field in CATEGORY_BY_CAPABILITY:
                    _ensure_profile_shell(u, CATEGORY_BY_CAPABILITY[field])

    if not changed:
        return jsonify({
            'ok': True,
            'user': u.to_dict(),
            'capabilities': u.capabilities_dict(),
            'profiles': _profile_snapshot(u),
        })

    db.session.commit()
    return jsonify({
        'ok': True,
        'user': u.to_dict(),
        'capabilities': u.capabilities_dict(),
        'profiles': _profile_snapshot(u),
    })


@super_users_bp.post('/<uuid:user_id>/suspend')
@require_role('super_admin')
def suspend_user(user: User, user_id):
    u = db.session.get(User, user_id)
    if not u:
        return not_found('User not found.')
    if u.id == user.id:
        return conflict('You cannot suspend your own account.')
    u.status = 'suspended'
    db.session.commit()
    return jsonify({'ok': True})


@super_users_bp.post('/<uuid:user_id>/unsuspend')
@require_role('super_admin')
def unsuspend_user(user: User, user_id):
    u = db.session.get(User, user_id)
    if not u:
        return not_found('User not found.')
    u.status = 'active'
    db.session.commit()
    return jsonify({'ok': True})


@super_users_bp.post('/<uuid:user_id>/reset-password')
@require_role('super_admin')
def reset_user_password(user: User, user_id):
    u = db.session.get(User, user_id)
    if not u:
        return not_found('User not found.')
    data = request.get_json(silent=True) or {}
    channels = data.get('delivery_channels') or ['email']
    channels = [c for c in channels if c in ('email', 'whatsapp', 'sms')]
    if not channels:
        return validation_failed('Pick at least one delivery channel.')

    temp = generate_temp_password()
    u.password_hash = hash_password(temp)
    u.password_reset_required = True

    dispatch_temp_password(
        recipient_email=u.email,
        recipient_phone=u.phone,
        channels=channels,
        full_name=u.name,
        temp_password=temp,
    )

    db.session.commit()
    return jsonify({'ok': True, 'temp_password': temp, 'delivery_channels': channels})
