"""ServiceHandler — the `bookable_type='service_provider'` handler for
BookingInterface. Per STAGE_4_SPEC.md §5.3.

KEY DESIGN POINTS:
  - The bookable is the SERVICE (provider_services row id), NOT the provider.
    Each catalog service is its own bookable_id; the provider's availability
    (rules + blocks + confirmed bookings, owned by BI) gates them ALL
    uniformly because conflict detection runs at the provider level.
  - NO payment integration. None of the hooks move money. rate_usd is
    informational; payment is off-platform between buyer and provider.
  - domain_payload convention:
        {service_id, buyer_notes, buyer_phone_at_request, distance_km|null}
"""
import logging
from uuid import UUID as _UUID

from extensions import db
from app.modules.booking_interface.handlers import BookingHandlerError
from app.modules.booking_interface.services.availability import range_is_bookable

from ..models import ProviderService


log = logging.getLogger('zimhub.services_section.handler')


def _coerce_uuid(v):
    if isinstance(v, _UUID):
        return v
    return _UUID(str(v))


def _load_active_service(service_id):
    try:
        sid = _coerce_uuid(service_id)
    except (ValueError, TypeError, AttributeError):
        raise BookingHandlerError('invalid_bookable', 'Invalid service id.', 400)
    service = db.session.get(ProviderService, sid)
    if not service:
        raise BookingHandlerError('unknown_bookable', 'No such service.', 404)
    return service


class ServiceHandler:
    """Plugged into BookingInterface's registry under 'service_provider'."""
    BOOKABLE_TYPE = 'service_provider'
    PROVIDER_CAPABILITY = 'is_provider'

    # ------------------------------------------------------------------
    @staticmethod
    def resolve_bookable(service_id, domain_payload=None):
        """service_id is the provider_services row id (NOT the provider
        user_id) — the elegant trick. Returns provider/timezone/rate info;
        rate is informational only, BI does NOT move money."""
        service = _load_active_service(service_id)
        if service.status != 'active':
            raise BookingHandlerError('inactive_service',
                                      'This service is no longer offered.', 409)
        provider = service.provider
        from app.modules.booking_interface.models import BIProviderProfile
        bi_prof = BIProviderProfile.query.filter_by(
            provider_id=service.provider_user_id).first()
        host_prof = getattr(provider, 'provider_profile', None)
        tz = (bi_prof.timezone if bi_prof else None) \
            or (host_prof.timezone if host_prof else None) or 'Africa/Harare'
        return {
            'provider_id': service.provider_user_id,
            'timezone': tz,
            'label': f"{(bi_prof.display_name if bi_prof else provider.name)} — {service.name}",
            'pricing_unit': service.pricing_unit,
            'rate_usd': service.rate_usd,            # informational only
            'default_duration_minutes': service.default_duration_minutes,
            'min_hours': bi_prof.min_hours if bi_prof else None,
            'max_hours': bi_prof.max_hours if bi_prof else None,
            'currency': 'USD',                        # informational
        }

    # ------------------------------------------------------------------
    @staticmethod
    def is_open(service_id, start_at, end_at):
        """Defers to BI's rule evaluation against the PROVIDER's calendar —
        Stage 4 just supplies the provider_id lookup."""
        service = _load_active_service(service_id)
        ok, _reason = range_is_bookable(service.provider_user_id, start_at, end_at)
        return ok

    # ------------------------------------------------------------------
    # Lifecycle hooks — no money anywhere. BI owns state + notifications.
    # ------------------------------------------------------------------
    @staticmethod
    def on_request(booking, domain_payload=None):
        """No-op — BI dispatches the canonical notification. Kept as the
        seam where Stage 5+ could attach extra metadata."""

    @staticmethod
    def on_confirm(booking, domain_payload=None):
        """No-op. BI fires confirmation notifications to both parties."""

    @staticmethod
    def on_decline(booking, domain_payload=None):
        """No-op."""

    @staticmethod
    def on_cancel(booking, domain_payload=None):
        """No-op."""

    @staticmethod
    def on_complete(booking, domain_payload=None):
        """Analytics hook for ranking — ranking computes live from the BI
        bookings table (§5.4), so nothing to persist here."""

    @staticmethod
    def on_no_show(booking, domain_payload=None):
        """Analytics hook — ranking reads final state on next compute."""

    @staticmethod
    def on_dispute_resolution(booking, resolution, domain_payload=None):
        """No-op. BI's dispute desk owns transitions; ranking reads final
        state on next compute."""
