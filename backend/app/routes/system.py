"""System routes — per spec §5.6.

Includes the small public /api/config/public endpoint (spec §6.4) used by the
DEMO MODE banner before login.
"""
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from extensions import db
from app.models import User, SellerSignupRequest, MockMessage
from app.services import host
from app.utils.decorators import require_role
from app.utils.errors import validation_failed


system_bp = Blueprint('system', __name__)


# ---------------------------------------------------------------------------
# Public — read-only config slice safe for anonymous callers.
# Used by DEMO MODE banner pre-login.
# ---------------------------------------------------------------------------
@system_bp.get('/api/config/public')
def public_config():
    return jsonify({
        'demo_mode': bool(host.config('DEMO_MODE', True)),
        'default_currency': host.config('DEFAULT_CURRENCY', 'USD'),
    })


# ---------------------------------------------------------------------------
# Super admin — dashboard
# ---------------------------------------------------------------------------
@system_bp.get('/api/super/dashboard-stats')
@require_role('super_admin')
def dashboard_stats(user: User):
    total_users = User.query.count()
    by_capability = {
        'is_buyer': User.query.filter_by(is_buyer=True).count(),
        'is_salesman': User.query.filter_by(is_salesman=True).count(),
        'is_promoter': User.query.filter_by(is_promoter=True).count(),
        'is_provider': User.query.filter_by(is_provider=True).count(),
        'is_creator': User.query.filter_by(is_creator=True).count(),
        'is_super_admin': User.query.filter_by(is_super_admin=True).count(),
    }

    counts_rows = db.session.query(
        SellerSignupRequest.status, func.count(SellerSignupRequest.id)
    ).group_by(SellerSignupRequest.status).all()
    signup_counts = {'pending': 0, 'approved': 0, 'rejected': 0}
    for s, n in counts_rows:
        signup_counts[s] = n

    # Mock-messages today (UTC day boundary; we display Africa/Harare on FE).
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    mock_today = MockMessage.query.filter(MockMessage.created_at >= today_start).count()

    # Recent activity — last 20 mixed events.
    recent_signups = (
        SellerSignupRequest.query
        .order_by(SellerSignupRequest.created_at.desc())
        .limit(20).all()
    )
    recent_users = (
        User.query.order_by(User.created_at.desc()).limit(20).all()
    )

    events = []
    for r in recent_signups:
        events.append({
            'kind': 'signup_request_' + r.status,
            'at': (r.reviewed_at or r.created_at).isoformat() if (r.reviewed_at or r.created_at) else None,
            'title': f"{r.full_name} — {r.category} application ({r.status})",
            'ref': str(r.id),
        })
    for u in recent_users:
        events.append({
            'kind': 'user_created',
            'at': u.created_at.isoformat() if u.created_at else None,
            'title': f"{u.name} joined ({u.email})",
            'ref': str(u.id),
        })
    events.sort(key=lambda e: e['at'] or '', reverse=True)

    return jsonify({
        'users': {'total': total_users, 'by_capability': by_capability},
        'signup_requests': signup_counts,
        'mock_messages_today': mock_today,
        'recent_activity': events[:20],
    })


# ---------------------------------------------------------------------------
# Super admin — config
# ---------------------------------------------------------------------------
@system_bp.get('/api/super/config')
@require_role('super_admin')
def get_config(user: User):
    return jsonify({'config': host.all_config()})


_EDITABLE_KEYS = (
    'HOLD_HOURS',
    'SETTLE_HOURS',
    'DEMO_MODE',
    'EVENT_MODERATION',
    'DEFAULT_CURRENCY',
    'RESPONSE_HOURS',
    'CANCEL_CUTOFF_HOURS',
    'DEFAULT_TIMEZONE',
)


@system_bp.put('/api/super/config')
@require_role('super_admin')
def put_config(user: User):
    data = request.get_json(silent=True) or {}
    errors = {}
    coerced = {}
    for k, v in data.items():
        if k not in _EDITABLE_KEYS:
            continue
        if k in ('HOLD_HOURS', 'SETTLE_HOURS', 'RESPONSE_HOURS', 'CANCEL_CUTOFF_HOURS'):
            if v is None or v == '':
                coerced[k] = None
            else:
                try:
                    coerced[k] = int(v)
                    if coerced[k] < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    errors[k] = 'Must be a non-negative integer (or empty for none).'
        elif k in ('DEMO_MODE', 'EVENT_MODERATION'):
            coerced[k] = bool(v)
        else:
            coerced[k] = str(v) if v is not None else None

    if errors:
        return validation_failed('Some config values are invalid.', field_errors=errors)

    for k, v in coerced.items():
        host.set_config(k, v)

    return jsonify({'ok': True, 'config': host.all_config()})


# ---------------------------------------------------------------------------
# Super admin — mock-messages viewer
# ---------------------------------------------------------------------------
@system_bp.get('/api/super/mock-messages')
@require_role('super_admin')
def list_mock_messages(user: User):
    channel = request.args.get('channel')
    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    page_size = 50

    query = MockMessage.query
    if channel in ('email', 'sms', 'whatsapp'):
        query = query.filter_by(channel=channel)
    total = query.count()
    rows = (
        query.order_by(MockMessage.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size).all()
    )
    return jsonify({
        'messages': [m.to_dict() for m in rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })
