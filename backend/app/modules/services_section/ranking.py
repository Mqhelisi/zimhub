"""Top providers ranking — STAGE_4_SPEC.md §5.4.

Top 8 active providers with ≥1 active service, ordered by COUNT(completed
bookings in the last 30 days) desc; tiebreaker: most active services listed.
Fresh compute on each call — caching is a later optimisation. No "top
services" list (services are too provider-specific to rank across providers).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from extensions import db
from app.models import User
from app.modules.booking_interface.models import Booking

from .models import ProviderService


def top_providers(limit=8):
    """Returns [(user, completed_30d, active_services)] ranked."""
    since = datetime.now(timezone.utc) - timedelta(days=30)

    completed = dict(
        db.session.query(Booking.provider_id, func.count(Booking.id))
        .filter(Booking.status == 'completed', Booking.completed_at >= since)
        .group_by(Booking.provider_id)
        .all()
    )
    service_counts = dict(
        db.session.query(ProviderService.provider_user_id,
                         func.count(ProviderService.id))
        .filter(ProviderService.status == 'active')
        .group_by(ProviderService.provider_user_id)
        .all()
    )
    if not service_counts:
        return []

    users = (User.query
             .filter(User.id.in_(list(service_counts.keys())),
                     User.is_provider.is_(True),
                     User.status == 'active')
             .all())
    ranked = sorted(
        users,
        key=lambda u: (-completed.get(u.id, 0), -service_counts.get(u.id, 0),
                       u.name.lower()),
    )
    return [(u, completed.get(u.id, 0), service_counts.get(u.id, 0))
            for u in ranked[:limit]]
