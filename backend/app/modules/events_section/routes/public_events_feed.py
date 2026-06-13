"""Unified public Events feed — Stage 3 §5.3 / §5.2.

GET /api/events             — paginated list, ticketed + flyer mixed
GET /api/events/:id         — already provided by TG public_events_bp
GET /api/events/categories  — list
GET /api/events/top         — top events + top promoters
"""
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from sqlalchemy import or_

from extensions import db
from app.modules.ticket_generator.models import Event, EVENT_CATEGORIES

from ..ranking import top_events, top_promoters


public_events_feed_bp = Blueprint('events_section_public', __name__,
                                  url_prefix='/api')


def _parse_date(s):
    if not s:
        return None
    try:
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


@public_events_feed_bp.get('/events')
def list_events_unified():
    """Unified feed mixing ticketed and flyer events.

    Query params:
      ?category=Music | Church | ...
      ?mode=all|ticketed|flyer
      ?date_from=ISO   ?date_to=ISO
      ?q=search string
      ?timing=upcoming|past|all      (default upcoming — past appear as muted)
      ?page=N (1-based)
    """
    category = (request.args.get('category') or '').strip()
    mode = (request.args.get('mode') or 'all').strip().lower()
    q_str = (request.args.get('q') or '').strip()
    date_from = _parse_date(request.args.get('date_from'))
    date_to = _parse_date(request.args.get('date_to'))
    timing = (request.args.get('timing') or 'all').strip().lower()
    try:
        page = max(1, int(request.args.get('page') or 1))
    except ValueError:
        page = 1
    page_size = 24

    q = Event.query.filter(
        Event.status.in_(('active', 'cancelled', 'archived'))
    )
    if mode == 'ticketed':
        q = q.filter(Event.mode == 'ticketed')
    elif mode == 'flyer':
        q = q.filter(Event.mode == 'flyer')
    if category and category in EVENT_CATEGORIES:
        q = q.filter(Event.category == category)
    if date_from:
        q = q.filter(Event.start_at >= date_from)
    if date_to:
        q = q.filter(Event.start_at <= date_to)
    now = datetime.now(timezone.utc)
    if timing == 'upcoming':
        q = q.filter(Event.end_at >= now)
    elif timing == 'past':
        q = q.filter(Event.end_at < now)
    # 'all' = no extra filter, but order makes upcoming come first.
    if q_str:
        like = f'%{q_str}%'
        q = q.filter(or_(Event.title.ilike(like),
                         Event.description.ilike(like),
                         Event.location.ilike(like)))

    # Upcoming asc then past desc — single SQL is hard, do two queries and merge.
    upcoming_q = (Event.query.from_self() if False else q).filter(Event.end_at >= now)
    past_q = q.filter(Event.end_at < now)

    upcoming = upcoming_q.order_by(Event.start_at.asc()).all()
    past = past_q.order_by(Event.start_at.desc()).all()

    combined = upcoming + past
    total = len(combined)
    start_i = (page - 1) * page_size
    end_i = start_i + page_size
    page_rows = combined[start_i:end_i]

    return jsonify({
        'events': [e.to_dict(include_ticket_types=True) for e in page_rows],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@public_events_feed_bp.get('/events/categories')
def list_categories_public():
    return jsonify({'categories': list(EVENT_CATEGORIES)})


@public_events_feed_bp.get('/events/top')
def feed_top():
    return jsonify({
        'top_events': top_events(limit=5),
        'top_promoters': top_promoters(limit=3),
    })
