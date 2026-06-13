"""BookingInterface provider availability routes — BI spec §8.

    GET    /api/provider/availability/rules
    POST   /api/provider/availability/rules
    DELETE /api/provider/availability/rules/:ruleId
    GET    /api/provider/availability/blocks?from=&to=
    POST   /api/provider/availability/blocks
    DELETE /api/provider/availability/blocks/:blockId
    GET    /api/provider/calendar?from=&to=

Note: GET/PUT /api/provider/profile is served by the Stage 4 services_section
module with a merged payload (host profile + the BI settings this module
owns) — one endpoint satisfying both specs' purposes. See
services_section/routes/provider_admin.py.
"""
import logging
from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone

from flask import Blueprint, request, jsonify

from extensions import db
from app.utils.decorators import require_role
from app.utils.errors import validation_failed, not_found

from ..models import AvailabilityRule, AvailabilityBlock, Booking
from ..services import booking_label


log = logging.getLogger('zimhub.booking_interface.availability')

availability_bp = Blueprint('booking_interface_availability', __name__,
                            url_prefix='/api/provider')


def _parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _parse_time(value):
    try:
        h, m = str(value).split(':')[:2]
        return dt_time(int(h), int(m))
    except Exception:
        return None


# ----------------------------------------------------------------------
# Recurring weekly rules
# ----------------------------------------------------------------------
@availability_bp.get('/availability/rules')
@require_role('provider')
def list_rules(user):
    rules = (AvailabilityRule.query
             .filter_by(provider_id=user.id)
             .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time)
             .all())
    return jsonify({'rules': [r.to_dict() for r in rules]})


@availability_bp.post('/availability/rules')
@require_role('provider')
def add_rule(user):
    data = request.get_json(silent=True) or {}
    weekday = data.get('weekday')
    start_time = _parse_time(data.get('start_time'))
    end_time = _parse_time(data.get('end_time'))
    if weekday is None or not isinstance(weekday, int) or not (0 <= weekday <= 6):
        return validation_failed('weekday must be an integer 0 (Mon) – 6 (Sun).')
    if not start_time or not end_time or start_time >= end_time:
        return validation_failed('start_time must be before end_time (HH:MM).')
    rule = AvailabilityRule(provider_id=user.id, weekday=weekday,
                            start_time=start_time, end_time=end_time)
    db.session.add(rule)
    db.session.commit()
    return jsonify({'rule': rule.to_dict()}), 201


@availability_bp.delete('/availability/rules/<uuid:rule_id>')
@require_role('provider')
def delete_rule(user, rule_id):
    rule = db.session.get(AvailabilityRule, rule_id)
    if not rule or str(rule.provider_id) != str(user.id):
        return not_found('Rule not found.')
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'ok': True})


# ----------------------------------------------------------------------
# One-off blocks
# ----------------------------------------------------------------------
@availability_bp.get('/availability/blocks')
@require_role('provider')
def list_blocks(user):
    q = AvailabilityBlock.query.filter_by(provider_id=user.id)
    from_dt = _parse_dt(request.args.get('from'))
    to_dt = _parse_dt(request.args.get('to'))
    if from_dt:
        q = q.filter(AvailabilityBlock.end_at > from_dt)
    if to_dt:
        q = q.filter(AvailabilityBlock.start_at < to_dt)
    blocks = q.order_by(AvailabilityBlock.start_at).all()
    return jsonify({'blocks': [b.to_dict() for b in blocks]})


@availability_bp.post('/availability/blocks')
@require_role('provider')
def add_block(user):
    data = request.get_json(silent=True) or {}
    start_at = _parse_dt(data.get('start_at'))
    end_at = _parse_dt(data.get('end_at'))
    if not start_at or not end_at or start_at >= end_at:
        return validation_failed('start_at must be before end_at (ISO datetimes).')
    block = AvailabilityBlock(provider_id=user.id, start_at=start_at,
                              end_at=end_at,
                              reason=(data.get('reason') or '').strip() or None)
    db.session.add(block)
    db.session.commit()
    return jsonify({'block': block.to_dict()}), 201


@availability_bp.delete('/availability/blocks/<uuid:block_id>')
@require_role('provider')
def delete_block(user, block_id):
    block = db.session.get(AvailabilityBlock, block_id)
    if not block or str(block.provider_id) != str(user.id):
        return not_found('Block not found.')
    db.session.delete(block)
    db.session.commit()
    return jsonify({'ok': True})


# ----------------------------------------------------------------------
# Resolved calendar — provider sees requester details (BI spec §8)
# ----------------------------------------------------------------------
@availability_bp.get('/calendar')
@require_role('provider')
def provider_calendar(user):
    from_dt = _parse_dt(request.args.get('from'))
    to_dt = _parse_dt(request.args.get('to'))
    if not from_dt or not to_dt or to_dt <= from_dt:
        return validation_failed("Valid 'from' and 'to' ISO datetimes are required.")
    if to_dt - from_dt > timedelta(days=93):
        return validation_failed('Window must be at most 93 days.')

    bookings = (Booking.query
                .filter(Booking.provider_id == user.id,
                        Booking.start_at < to_dt,
                        Booking.end_at > from_dt)
                .order_by(Booking.start_at)
                .all())
    rules = (AvailabilityRule.query.filter_by(provider_id=user.id)
             .order_by(AvailabilityRule.weekday, AvailabilityRule.start_time).all())
    blocks = (AvailabilityBlock.query
              .filter(AvailabilityBlock.provider_id == user.id,
                      AvailabilityBlock.start_at < to_dt,
                      AvailabilityBlock.end_at > from_dt)
              .order_by(AvailabilityBlock.start_at).all())

    return jsonify({
        'bookings': [b.to_dict(viewer=user, label=booking_label(b)) for b in bookings],
        'availability_rules': [r.to_dict() for r in rules],
        'time_blocks': [b.to_dict() for b in blocks],
    })
