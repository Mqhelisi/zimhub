"""Availability resolution — BOOKING_INTERFACE_SPEC.md §6.

A requested range [start_at, end_at) is bookable only if ALL hold:
  1. Inside a recurring availability rule (provider's timezone, per weekday).
  2. Not overlapping any one-off availability block.
  3. No confirmed-booking overlap (half-open ranges; back-to-back is fine).
  4. Aligned to SLOT_GRANULARITY_MINUTES and within MIN/MAX hours if set.
  5. start_at >= now() + LEAD_TIME_HOURS, and start_at strictly in the future.

Pending (`requested`) bookings are deliberately IGNORED here — the busy set
is confirmed bookings + blocks only. Double-booking is prevented at accept.
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from app.services import host

from ..models import (
    BIProviderProfile, AvailabilityRule, AvailabilityBlock, Booking,
)


def _now():
    return datetime.now(dt_timezone.utc)


def _tz_for(provider_id) -> ZoneInfo:
    prof = BIProviderProfile.query.filter_by(provider_id=provider_id).first()
    name = (prof.timezone if prof and prof.timezone else None) \
        or host.config('DEFAULT_TIMEZONE', 'Africa/Harare') or 'Africa/Harare'
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo('Africa/Harare')


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    """Half-open [start, end) overlap — back-to-back does NOT overlap."""
    return a_start < b_end and b_start < a_end


def _inside_rules(provider_id, start_at, end_at, tz: ZoneInfo) -> bool:
    """True iff every point of [start_at, end_at) is inside the provider's
    recurring open hours, evaluated in the provider's local timezone.

    A range may span midnight only if contiguous rules cover it; for v1 the
    practical case is same-local-day ranges, checked day by day.
    """
    rules = AvailabilityRule.query.filter_by(provider_id=provider_id).all()
    if not rules:
        return False
    by_day = {}
    for r in rules:
        by_day.setdefault(r.weekday, []).append((r.start_time, r.end_time))

    cursor = start_at.astimezone(tz)
    end_local = end_at.astimezone(tz)
    while cursor < end_local:
        day_end = (cursor.replace(hour=0, minute=0, second=0, microsecond=0)
                   + timedelta(days=1))
        segment_end = min(end_local, day_end)
        windows = by_day.get(cursor.weekday(), [])
        seg_s, seg_e = cursor.time(), segment_end.time()
        # segment ending exactly at midnight -> compare against 24:00
        seg_e_minutes = (24 * 60 if segment_end == day_end
                         else seg_e.hour * 60 + seg_e.minute)
        seg_s_minutes = seg_s.hour * 60 + seg_s.minute
        covered = any(
            (w_s.hour * 60 + w_s.minute) <= seg_s_minutes
            and seg_e_minutes <= (w_e.hour * 60 + w_e.minute)
            for w_s, w_e in windows
        )
        if not covered:
            return False
        cursor = segment_end
    return True


def _blocked(provider_id, start_at, end_at) -> bool:
    q = AvailabilityBlock.query.filter(
        AvailabilityBlock.provider_id == provider_id,
        AvailabilityBlock.start_at < end_at,
        AvailabilityBlock.end_at > start_at,
    )
    return db_exists(q)


def _confirmed_overlap(provider_id, start_at, end_at, exclude_booking_id=None) -> bool:
    q = Booking.query.filter(
        Booking.provider_id == provider_id,
        Booking.status == 'confirmed',
        Booking.start_at < end_at,
        Booking.end_at > start_at,
    )
    if exclude_booking_id is not None:
        q = q.filter(Booking.id != exclude_booking_id)
    return db_exists(q)


def db_exists(query) -> bool:
    return query.first() is not None


def range_is_bookable(provider_id, start_at, end_at, *,
                      min_hours=None, max_hours=None,
                      exclude_booking_id=None):
    """Full §6 check. Returns (ok: bool, reason: str|None)."""
    start_at = _as_utc(start_at)
    end_at = _as_utc(end_at)
    if start_at >= end_at:
        return False, 'invalid_range'

    now = _now()
    lead_hours = int(host.config('LEAD_TIME_HOURS', 0) or 0)
    if start_at < now + timedelta(hours=lead_hours) or start_at <= now:
        return False, 'past_or_too_soon'

    gran = int(host.config('SLOT_GRANULARITY_MINUTES', 60) or 60)
    for dt in (start_at, end_at):
        local = dt.astimezone(_tz_for(provider_id))
        total_min = local.hour * 60 + local.minute
        if total_min % gran != 0 or local.second or local.microsecond:
            return False, 'granularity'

    duration_h = (end_at - start_at).total_seconds() / 3600.0
    prof = BIProviderProfile.query.filter_by(provider_id=provider_id).first()
    eff_min = min_hours if min_hours is not None else (prof.min_hours if prof else None)
    eff_max = max_hours if max_hours is not None else (prof.max_hours if prof else None)
    if eff_min is not None and duration_h < eff_min:
        return False, 'below_min_hours'
    if eff_max is not None and duration_h > eff_max:
        return False, 'above_max_hours'

    tz = _tz_for(provider_id)
    if not _inside_rules(provider_id, start_at, end_at, tz):
        return False, 'outside_availability'
    if _blocked(provider_id, start_at, end_at):
        return False, 'blocked'
    if _confirmed_overlap(provider_id, start_at, end_at,
                          exclude_booking_id=exclude_booking_id):
        return False, 'slot_unavailable'
    return True, None


def free_slots(provider_id, from_dt, to_dt, *, granularity_minutes=None):
    """Enumerate bookable slot starts (granularity-sized cells) in a window.

    Returns (available, busy) lists of {start_at, end_at} ISO dicts. `busy`
    is opaque — confirmed bookings + blocks merged; no requester details
    leak (BI spec §8 public availability endpoint).
    """
    from_dt = _as_utc(from_dt)
    to_dt = _as_utc(to_dt)
    gran = int(granularity_minutes
               or host.config('SLOT_GRANULARITY_MINUTES', 60) or 60)
    tz = _tz_for(provider_id)

    rules = AvailabilityRule.query.filter_by(provider_id=provider_id).all()
    by_day = {}
    for r in rules:
        by_day.setdefault(r.weekday, []).append((r.start_time, r.end_time))

    blocks = AvailabilityBlock.query.filter(
        AvailabilityBlock.provider_id == provider_id,
        AvailabilityBlock.start_at < to_dt,
        AvailabilityBlock.end_at > from_dt,
    ).all()
    confirmed = Booking.query.filter(
        Booking.provider_id == provider_id,
        Booking.status == 'confirmed',
        Booking.start_at < to_dt,
        Booking.end_at > from_dt,
    ).all()

    now = _now()
    lead_hours = int(host.config('LEAD_TIME_HOURS', 0) or 0)
    earliest = max(from_dt, now + timedelta(hours=lead_hours))

    available, busy = [], []
    for b in confirmed:
        busy.append({'start_at': _as_utc(b.start_at).isoformat(),
                     'end_at': _as_utc(b.end_at).isoformat(), 'kind': 'booked'})
    for bl in blocks:
        busy.append({'start_at': _as_utc(bl.start_at).isoformat(),
                     'end_at': _as_utc(bl.end_at).isoformat(), 'kind': 'blocked'})

    # Walk local days, expand each rule window into granularity cells.
    cursor_local = from_dt.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = to_dt.astimezone(tz)
    while cursor_local < end_local:
        for (w_s, w_e) in by_day.get(cursor_local.weekday(), []):
            slot_local = cursor_local.replace(hour=w_s.hour, minute=w_s.minute)
            window_end_local = cursor_local.replace(hour=w_e.hour, minute=w_e.minute)
            while slot_local + timedelta(minutes=gran) <= window_end_local:
                s_utc = slot_local.astimezone(dt_timezone.utc)
                e_utc = (slot_local + timedelta(minutes=gran)).astimezone(dt_timezone.utc)
                if s_utc >= earliest and s_utc < to_dt and s_utc > now:
                    clash = any(
                        _overlaps(s_utc, e_utc, _as_utc(b.start_at), _as_utc(b.end_at))
                        for b in confirmed
                    ) or any(
                        _overlaps(s_utc, e_utc, _as_utc(bl.start_at), _as_utc(bl.end_at))
                        for bl in blocks
                    )
                    if not clash:
                        available.append({'start_at': s_utc.isoformat(),
                                          'end_at': e_utc.isoformat()})
                slot_local += timedelta(minutes=gran)
        cursor_local += timedelta(days=1)

    available.sort(key=lambda s: s['start_at'])
    busy.sort(key=lambda s: s['start_at'])
    return available, busy
