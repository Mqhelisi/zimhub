"""Notifications — per spec §5.5."""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from extensions import db
from app.models import User, Notification
from app.utils.decorators import require_auth
from app.utils.errors import not_found, forbidden


notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.get('')
@require_auth
def list_notifications(user: User):
    unread_only = (request.args.get('unread', '').lower() in ('1', 'true', 'yes'))
    try:
        page = max(int(request.args.get('page', 1)), 1)
    except (ValueError, TypeError):
        page = 1
    page_size = 20

    query = Notification.query.filter_by(user_id=user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))

    rows = (
        query.order_by(Notification.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )
    unread_count = Notification.query.filter_by(user_id=user.id, read_at=None).count()
    return jsonify({
        'notifications': [n.to_dict() for n in rows],
        'unread_count': unread_count,
        'page': page,
        'page_size': page_size,
    })


@notifications_bp.post('/<uuid:notif_id>/read')
@require_auth
def mark_read(user: User, notif_id):
    n = db.session.get(Notification, notif_id)
    if not n:
        return not_found('Notification not found.')
    if str(n.user_id) != str(user.id):
        return forbidden('Not your notification.')
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.session.commit()
    return jsonify({'ok': True})


@notifications_bp.post('/read-all')
@require_auth
def mark_all_read(user: User):
    now = datetime.now(timezone.utc)
    n = (
        Notification.query.filter_by(user_id=user.id, read_at=None)
                          .update({'read_at': now})
    )
    db.session.commit()
    return jsonify({'ok': True, 'marked': n})
