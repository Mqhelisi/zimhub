"""Public events endpoints — per TG spec §9.

The unified `/api/events` feed is owned by `events_section` (Stage 3, mixes
ticketed + flyer). This file provides:

  - GET /api/events/by-tg                    (ticketed-only list; debug aid)
  - GET /api/events/:id                      (single-event detail, both modes)

The detail endpoint is here because event detail is TG's domain (ticket types
live on TG). events_section can — and does — delegate detail to this endpoint
by calling the function directly OR via the canonical URL.
"""
from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.errors import not_found

from ..models import Event


public_events_bp = Blueprint('tg_public_events', __name__, url_prefix='/api')


@public_events_bp.get('/events/by-tg')
def list_ticketed_events():
    """Quick list of ticketed-only events for compatibility / debugging.

    The canonical public feed lives in events_section at GET /api/events.
    """
    category = (request.args.get('category') or '').strip()
    q = Event.query.filter(Event.mode == 'ticketed', Event.status == 'active')
    if category:
        q = q.filter(Event.category == category)
    rows = q.order_by(Event.start_at.asc()).limit(200).all()
    return jsonify({'events': [e.to_dict(include_ticket_types=False) for e in rows]})


@public_events_bp.get('/events/<event_id>')
def event_detail(event_id):
    e = db.session.get(Event, event_id)
    if not e:
        return not_found('Event not found.')
    # Public detail: only active / cancelled / archived. Hide draft/pending.
    if e.status in ('draft', 'pending_approval', 'rejected'):
        # Allow the promoter to see their own draft via the promoter endpoint.
        return not_found('Event not found.')
    return jsonify({'event': e.to_dict(include_ticket_types=True)})
