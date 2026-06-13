"""Booking state machine — BOOKING_INTERFACE_SPEC.md §4 / §12.

Public functions are the ONLY way to mutate a Booking row. Routes call into
this module. Functions do not commit — the caller owns the transaction —
EXCEPT the sweepers, which commit batches themselves (they run outside a
request).

Concurrency: accept_booking serialises with SELECT … FOR UPDATE over the
provider's confirmed bookings overlapping the range, re-checks availability,
then locks the slot and auto-declines clashing pending requests
(reason: slot_taken).

No money handshake anywhere — rates are informational; payment is
off-platform (BI spec §1/§12). Notifications must not imply platform payment.
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal

from extensions import db
from app.services import host

from ..handlers import get_bookable_handler, BookingHandlerError
from ..models import Booking, BookingEvent, BookingDispute, BIProviderProfile
from .availability import range_is_bookable


log = logging.getLogger('zimhub.booking_interface')


class BookingStateError(Exception):
    """Raised when a transition is illegal for the current state/role."""
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _now():
    return datetime.now(dt_timezone.utc)


def _as_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(dt_timezone.utc)


def _log_event(booking, from_status, to_status, actor_id, actor_role, note=None):
    e = BookingEvent(
        booking_id=booking.id, from_status=from_status, to_status=to_status,
        actor_id=actor_id, actor_role=actor_role, note=note,
    )
    db.session.add(e)
    return e


def booking_label(booking) -> str:
    try:
        handler = get_bookable_handler(booking.bookable_type)
        info = handler.resolve_bookable(booking.bookable_id,
                                        domain_payload=booking.domain_payload)
        return info.get('label') or f'Booking {str(booking.id)[:8]}'
    except Exception:
        return f'Booking {str(booking.id)[:8]}'


def _fmt_range(booking) -> str:
    s = _as_utc(booking.start_at)
    e = _as_utc(booking.end_at)
    return f"{s.strftime('%a %d %b %Y, %H:%M')}–{e.strftime('%H:%M')} UTC"


def build_whatsapp_link(booking, viewer_role: str) -> str:
    """Prefilled wa.me deep-link to the counterparty — BI spec §8.

    Date/time/duration + a 'to confirm details' note. Never implies the
    platform handled payment.
    """
    counterparty = booking.provider if viewer_role == 'requester' else booking.requester
    if counterparty is None:
        return ''
    label = booking_label(booking)
    text = (
        f"Hi {counterparty.name.split(' ')[0]}, about my ZimHub booking: {label}. "
        f"{_fmt_range(booking)} ({booking.duration_hours}h). "
        f"Messaging to confirm details. Reference: {str(booking.id)[:8]}"
    )
    return host.whatsapp_link(counterparty.phone, text)


# ---------------------------------------------------------------------------
# Notification fan-out — kinds per BI spec §11. In-app + mock transports
# through the host seam only.
# ---------------------------------------------------------------------------
def _notify(user, kind, title, body, booking):
    host.notify(user.id, kind, title, body, metadata={'booking_id': str(booking.id)})
    host.send('whatsapp', user.phone, f'{title} — {body}',
              payload={'booking_id': str(booking.id), 'kind': kind})


def _notify_requested(booking):
    _notify(booking.provider, 'booking_requested', 'New booking request',
            f'{booking.requester.name} requested {booking_label(booking)} '
            f'for {_fmt_range(booking)}.', booking)


def _notify_confirmed(booking):
    _notify(booking.requester, 'booking_confirmed', 'Booking confirmed',
            f'{booking.provider.name} accepted your booking: '
            f'{booking_label(booking)}, {_fmt_range(booking)}.', booking)


def _notify_declined(booking, reason=None):
    extra = f' Reason: {reason}.' if reason else ''
    _notify(booking.requester, 'booking_declined', 'Booking declined',
            f'{booking.provider.name} declined your request for '
            f'{booking_label(booking)}.{extra}', booking)


def _notify_cancelled(booking, cancelled_by_role):
    counterparty = booking.provider if cancelled_by_role == 'requester' else booking.requester
    who = booking.requester.name if cancelled_by_role == 'requester' else booking.provider.name
    _notify(counterparty, 'booking_cancelled', 'Booking cancelled',
            f'{who} cancelled the booking: {booking_label(booking)}, '
            f'{_fmt_range(booking)}.', booking)


def _notify_expired(booking):
    _notify(booking.requester, 'booking_expired', 'Booking request expired',
            f'{booking.provider.name} did not respond in time to your request '
            f'for {booking_label(booking)}.', booking)


def _notify_completed(booking):
    for u in (booking.requester, booking.provider):
        _notify(u, 'booking_completed', 'Booking completed',
                f'{booking_label(booking)} ({_fmt_range(booking)}) is complete.', booking)


def _notify_no_show(booking):
    _notify(booking.requester, 'booking_no_show', 'Marked as no-show',
            f'{booking.provider.name} flagged a no-show for '
            f'{booking_label(booking)}.', booking)


def _notify_dispute_raised(booking, dispute):
    counterparty = (booking.provider if dispute.raised_by_role == 'requester'
                    else booking.requester)
    _notify(counterparty, 'dispute_raised', 'Booking dispute raised',
            f'A dispute was raised on {booking_label(booking)}: {dispute.reason}', booking)
    # All dispute admins (super admins) get an in-app heads-up.
    from app.models import User
    for admin in User.query.filter_by(is_super_admin=True).all():
        host.notify(admin.id, 'dispute_raised', 'Booking dispute raised',
                    f'Dispute on booking {str(booking.id)[:8]}: {dispute.reason}',
                    metadata={'booking_id': str(booking.id),
                              'booking_dispute_id': str(dispute.id)})


def _notify_dispute_resolved(booking, dispute):
    for u in (booking.requester, booking.provider):
        _notify(u, 'dispute_resolved', 'Booking dispute resolved',
                f'Dispute on {booking_label(booking)} resolved: '
                f'{dispute.resolution}.', booking)


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------
def request_booking(*, requester, bookable_type: str, bookable_id,
                    start_at, end_at, message: str = None,
                    domain_payload: dict = None) -> Booking:
    """→ requested. Validated against availability (§6). Does NOT lock."""
    handler = get_bookable_handler(bookable_type or 'service_provider')
    info = handler.resolve_bookable(bookable_id, domain_payload=domain_payload)
    provider_id = info['provider_id']

    if str(provider_id) == str(requester.id):
        raise BookingStateError('own_profile',
                                'You cannot book your own provider profile.', 400)

    start_at = _as_utc(start_at)
    end_at = _as_utc(end_at)

    ok, reason = range_is_bookable(
        provider_id, start_at, end_at,
        min_hours=info.get('min_hours'), max_hours=info.get('max_hours'),
    )
    if not ok:
        raise BookingStateError('slot_unavailable',
                                f'That slot is not available ({reason}).', 409)
    # Handler-level availability check (domain may add constraints).
    if not handler.is_open(bookable_id, start_at, end_at):
        raise BookingStateError('slot_unavailable',
                                'That slot is not available.', 409)

    duration_h = Decimal((end_at - start_at).total_seconds() / 3600).quantize(Decimal('0.01'))

    # quoted_rate snapshot — informational only.
    quoted = None
    rate = info.get('rate_usd') or info.get('hourly_rate_usd')
    if rate is not None:
        try:
            quoted = (Decimal(str(rate)) * duration_h).quantize(Decimal('0.01')) \
                if info.get('pricing_unit') in (None, 'per_hour') \
                else Decimal(str(rate)).quantize(Decimal('0.01'))
        except Exception:
            quoted = None

    # expires_at = start_at by default; tightened by RESPONSE_HOURS if set.
    prof = BIProviderProfile.query.filter_by(provider_id=provider_id).first()
    response_hours = (prof.response_hours if prof and prof.response_hours
                      else host.config('RESPONSE_HOURS', None))
    expires_at = start_at
    if response_hours:
        expires_at = min(start_at, _now() + timedelta(hours=int(response_hours)))

    booking = Booking(
        bookable_type=bookable_type or 'service_provider',
        bookable_id=bookable_id,
        provider_id=provider_id,
        requester_id=requester.id,
        start_at=start_at, end_at=end_at,
        duration_hours=duration_h,
        status='requested',
        message=message,
        quoted_rate_usd=quoted,
        domain_payload=domain_payload or {},
        expires_at=expires_at,
    )
    db.session.add(booking)
    db.session.flush()
    _log_event(booking, None, 'requested', requester.id, 'requester')

    try:
        handler.on_request(booking, domain_payload)
    except BookingHandlerError:
        raise
    except Exception:
        log.exception('on_request hook failed for booking %s', booking.id)

    _notify_requested(booking)
    return booking


def accept_booking(*, booking: Booking, provider) -> Booking:
    """requested → confirmed. Provider only. Serialised; auto-declines
    overlapping pending requests with reason slot_taken."""
    if str(provider.id) != str(booking.provider_id):
        raise BookingStateError('forbidden', 'Only the provider can accept.', 403)
    if booking.status != 'requested':
        raise BookingStateError('invalid_state',
                                f'Cannot accept a booking in state {booking.status}.', 409)

    # Serialise: lock the provider's confirmed bookings overlapping the range.
    locked_overlaps = (
        db.session.query(Booking)
        .filter(
            Booking.provider_id == booking.provider_id,
            Booking.status == 'confirmed',
            Booking.start_at < booking.end_at,
            Booking.end_at > booking.start_at,
        )
        .with_for_update()
        .all()
    )
    if locked_overlaps:
        # A confirmed clash exists — the request stays `requested` (§4).
        raise BookingStateError('slot_taken', 'slot_taken', 409)

    # Availability re-validated at accept (§12) — a block or another confirmed
    # booking may have appeared since request time.
    ok, reason = range_is_bookable(
        booking.provider_id, booking.start_at, booking.end_at,
        exclude_booking_id=booking.id,
    )
    if not ok and reason == 'slot_unavailable':
        raise BookingStateError('slot_taken', 'slot_taken', 409)
    if not ok and reason not in ('past_or_too_soon',):
        # Past-start acceptance is tolerated up to expiry; other failures block.
        raise BookingStateError('slot_unavailable',
                                f'The slot is no longer available ({reason}).', 409)

    booking.status = 'confirmed'
    booking.provider_responded_at = _now()
    _log_event(booking, 'requested', 'confirmed', provider.id, 'provider')

    # Auto-decline every other pending request overlapping the locked range.
    clashing = Booking.query.filter(
        Booking.id != booking.id,
        Booking.provider_id == booking.provider_id,
        Booking.status == 'requested',
        Booking.start_at < booking.end_at,
        Booking.end_at > booking.start_at,
    ).all()
    for other in clashing:
        other.status = 'declined'
        other.provider_responded_at = _now()
        other.cancel_reason = 'slot_taken'
        _log_event(other, 'requested', 'declined', None, 'system', note='slot_taken')
        _notify_declined(other, reason='slot_taken')
        try:
            get_bookable_handler(other.bookable_type).on_decline(
                other, other.domain_payload)
        except Exception:
            log.exception('on_decline hook failed for booking %s', other.id)

    try:
        get_bookable_handler(booking.bookable_type).on_confirm(
            booking, booking.domain_payload)
    except Exception:
        log.exception('on_confirm hook failed for booking %s', booking.id)

    _notify_confirmed(booking)
    return booking


def decline_booking(*, booking: Booking, provider, reason: str = None) -> Booking:
    if str(provider.id) != str(booking.provider_id):
        raise BookingStateError('forbidden', 'Only the provider can decline.', 403)
    if booking.status != 'requested':
        raise BookingStateError('invalid_state',
                                f'Cannot decline a booking in state {booking.status}.', 409)
    booking.status = 'declined'
    booking.provider_responded_at = _now()
    if reason:
        booking.cancel_reason = reason
    _log_event(booking, 'requested', 'declined', provider.id, 'provider', note=reason)
    try:
        get_bookable_handler(booking.bookable_type).on_decline(
            booking, booking.domain_payload)
    except Exception:
        log.exception('on_decline hook failed for booking %s', booking.id)
    _notify_declined(booking, reason=reason)
    return booking


def cancel_booking(*, booking: Booking, user, reason: str = None) -> Booking:
    """requested|confirmed → cancelled. Either party, before start_at and
    outside CANCEL_CUTOFF_HOURS. Releases the lock; notifies the counterparty."""
    is_requester = str(user.id) == str(booking.requester_id)
    is_provider = str(user.id) == str(booking.provider_id)
    if not (is_requester or is_provider):
        raise BookingStateError('forbidden', 'Not your booking.', 403)
    if booking.status not in ('requested', 'confirmed'):
        raise BookingStateError('invalid_state',
                                f'Cannot cancel a booking in state {booking.status}.', 409)
    now = _now()
    if now >= _as_utc(booking.start_at):
        raise BookingStateError('too_late',
                                'The booking has already started; coordinate over WhatsApp.', 409)
    cutoff_hours = int(host.config('CANCEL_CUTOFF_HOURS', 0) or 0)
    prof = BIProviderProfile.query.filter_by(provider_id=booking.provider_id).first()
    if prof and prof.cancel_cutoff_hours is not None:
        cutoff_hours = prof.cancel_cutoff_hours
    if now > _as_utc(booking.start_at) - timedelta(hours=cutoff_hours):
        raise BookingStateError(
            'past_cutoff',
            'Past the cancellation cutoff — please coordinate over WhatsApp.', 409)

    role = 'requester' if is_requester else 'provider'
    from_status = booking.status
    booking.status = 'cancelled'
    booking.cancelled_by = role
    booking.cancel_reason = reason
    _log_event(booking, from_status, 'cancelled', user.id, role, note=reason)
    try:
        get_bookable_handler(booking.bookable_type).on_cancel(
            booking, booking.domain_payload)
    except Exception:
        log.exception('on_cancel hook failed for booking %s', booking.id)
    _notify_cancelled(booking, role)
    return booking


def mark_no_show(*, booking: Booking, provider) -> Booking:
    """confirmed → no_show. Provider only, after start_at."""
    if str(provider.id) != str(booking.provider_id):
        raise BookingStateError('forbidden', 'Only the provider can flag a no-show.', 403)
    if booking.status != 'confirmed':
        raise BookingStateError('invalid_state',
                                f'Cannot flag no-show in state {booking.status}.', 409)
    if _now() <= _as_utc(booking.start_at):
        raise BookingStateError('too_early',
                                'You can only flag a no-show after the start time.', 409)
    booking.status = 'no_show'
    booking.no_show = True
    _log_event(booking, 'confirmed', 'no_show', provider.id, 'provider')
    try:
        get_bookable_handler(booking.bookable_type).on_no_show(
            booking, booking.domain_payload)
    except Exception:
        log.exception('on_no_show hook failed for booking %s', booking.id)
    _notify_no_show(booking)
    return booking


def mark_complete(*, booking: Booking, provider) -> Booking:
    """confirmed → completed, provider-initiated, only after end_at.

    The sweeper also auto-completes; this is the manual path (Stage 4 §11.8:
    backend rejects early completion).
    """
    if str(provider.id) != str(booking.provider_id):
        raise BookingStateError('forbidden', 'Only the provider can mark complete.', 403)
    if booking.status != 'confirmed':
        raise BookingStateError('invalid_state',
                                f'Cannot complete a booking in state {booking.status}.', 409)
    if _now() <= _as_utc(booking.end_at):
        raise BookingStateError('too_early',
                                'You can only mark complete after the end time.', 409)
    if booking.has_open_dispute():
        raise BookingStateError('disputed', 'This booking has an open dispute.', 409)
    booking.status = 'completed'
    booking.completed_at = _now()
    _log_event(booking, 'confirmed', 'completed', provider.id, 'provider')
    try:
        get_bookable_handler(booking.bookable_type).on_complete(
            booking, booking.domain_payload)
    except Exception:
        log.exception('on_complete hook failed for booking %s', booking.id)
    _notify_completed(booking)
    return booking


def raise_dispute(*, booking: Booking, user, reason: str) -> BookingDispute:
    """→ disputed. Either party, on a cancellation/no-show they contest, or a
    live confirmed/completed booking. Freezes auto-complete; admin resolves."""
    is_requester = str(user.id) == str(booking.requester_id)
    is_provider = str(user.id) == str(booking.provider_id)
    if not (is_requester or is_provider):
        raise BookingStateError('forbidden', 'Not your booking.', 403)
    if not reason or not reason.strip():
        raise BookingStateError('validation_failed', 'A reason is required.', 400)
    if booking.has_open_dispute():
        raise BookingStateError('already_disputed',
                                'This booking already has an open dispute.', 409)
    if booking.status not in ('confirmed', 'completed', 'cancelled', 'no_show'):
        raise BookingStateError('invalid_state',
                                f'Cannot dispute a booking in state {booking.status}.', 409)

    role = 'requester' if is_requester else 'provider'
    dispute = BookingDispute(
        booking_id=booking.id, raised_by=user.id, raised_by_role=role,
        reason=reason.strip(), status='open',
    )
    db.session.add(dispute)
    db.session.flush()
    from_status = booking.status
    booking.status = 'disputed'
    booking.dispute_id = dispute.id
    _log_event(booking, from_status, 'disputed', user.id, role, note=reason)
    _notify_dispute_raised(booking, dispute)
    return dispute


def resolve_dispute(*, dispute: BookingDispute, admin, resolution: str,
                    note: str = None) -> BookingDispute:
    """disputed → completed | cancelled. Dispute admin only (host capability)."""
    if not host.is_dispute_admin(admin):
        raise BookingStateError('forbidden', 'Only a dispute admin can resolve.', 403)
    if dispute.status != 'open':
        raise BookingStateError('invalid_state', 'Dispute is already resolved.', 409)
    if resolution not in ('completed', 'cancelled'):
        raise BookingStateError('validation_failed',
                                "resolution must be 'completed' or 'cancelled'.", 400)
    booking = dispute.booking
    dispute.status = 'resolved'
    dispute.resolution = resolution
    dispute.resolution_note = note
    dispute.resolved_by = admin.id
    dispute.resolved_at = _now()

    from_status = booking.status
    booking.status = resolution
    if resolution == 'completed':
        booking.completed_at = booking.completed_at or _now()
    else:
        booking.cancelled_by = 'admin'
        booking.cancel_reason = note or 'Resolved by dispute admin.'
    _log_event(booking, from_status, resolution, admin.id, 'admin', note=note)
    try:
        get_bookable_handler(booking.bookable_type).on_dispute_resolution(
            booking, resolution, booking.domain_payload)
    except Exception:
        log.exception('on_dispute_resolution hook failed for booking %s', booking.id)
    _notify_dispute_resolved(booking, dispute)
    return dispute


# ---------------------------------------------------------------------------
# Sweepers — BI spec §9. Run every 60s on the shared APScheduler instance.
# These commit their own batches (they run outside any request).
# ---------------------------------------------------------------------------
def expire_bookings_due() -> int:
    """requested with expires_at < now() → expired; notify requester."""
    now = _now()
    due = Booking.query.filter(
        Booking.status == 'requested',
        Booking.expires_at.isnot(None),
        Booking.expires_at < now,
    ).all()
    n = 0
    for b in due:
        b.status = 'expired'
        _log_event(b, 'requested', 'expired', None, 'system')
        _notify_expired(b)
        n += 1
    if n:
        db.session.commit()
        log.info('Expired %d booking request(s).', n)
    return n


def complete_bookings_due() -> int:
    """confirmed with end_at < now(), no open dispute, no no-show flag →
    completed; notify both parties."""
    now = _now()
    due = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.end_at < now,
        Booking.no_show.is_(False),
    ).all()
    n = 0
    for b in due:
        if b.has_open_dispute():
            continue
        b.status = 'completed'
        b.completed_at = now
        _log_event(b, 'confirmed', 'completed', None, 'system')
        try:
            get_bookable_handler(b.bookable_type).on_complete(b, b.domain_payload)
        except Exception:
            log.exception('on_complete hook failed for booking %s', b.id)
        _notify_completed(b)
        n += 1
    if n:
        db.session.commit()
        log.info('Auto-completed %d booking(s).', n)
    return n
