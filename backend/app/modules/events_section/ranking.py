"""Top events / top promoters ranking — last 30 days, by completed Purchases.

Per Stage 3 §5.2 + §11.14. Flyer events are not ranked because they have no
Purchases.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import func

from extensions import db
from app.modules.purchase_interface.models import Purchase
from app.modules.ticket_generator.models import Event, TicketType


def top_events(limit=5):
    """Top ticketed events ranked by completed Purchases in last 30 days."""
    thirty_d = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (db.session.query(
                Event,
                func.count(Purchase.id).label('completed_count'),
                func.coalesce(func.sum(Purchase.total_usd), 0).label('revenue'),
            )
            .join(TicketType, TicketType.event_id == Event.id)
            .outerjoin(Purchase, (
                (Purchase.listing_type == 'event_ticket') &
                (Purchase.listing_id == TicketType.id) &
                (Purchase.status == 'completed') &
                (Purchase.completed_at >= thirty_d)
            ))
            .filter(Event.mode == 'ticketed', Event.status == 'active')
            .group_by(Event.id)
            .order_by(func.count(Purchase.id).desc(), Event.start_at.asc())
            .limit(limit).all())
    return [
        {
            'event': e.to_dict(include_ticket_types=False),
            'completed_purchases_30d': int(c or 0),
            'revenue_30d_usd': str(r or 0),
        }
        for (e, c, r) in rows
    ]


def top_promoters(limit=3):
    """Top promoters ranked by completed Purchase volume in last 30 days."""
    thirty_d = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (db.session.query(
                Event.promoter_id,
                func.count(Purchase.id).label('completed_count'),
                func.coalesce(func.sum(Purchase.total_usd), 0).label('revenue'),
            )
            .join(TicketType, TicketType.event_id == Event.id)
            .join(Purchase, (
                (Purchase.listing_type == 'event_ticket') &
                (Purchase.listing_id == TicketType.id) &
                (Purchase.status == 'completed') &
                (Purchase.completed_at >= thirty_d)
            ))
            .group_by(Event.promoter_id)
            .order_by(func.count(Purchase.id).desc())
            .limit(limit).all())

    from app.models import User
    from app.models.promoter_profile import PromoterProfile
    out = []
    for (pid, count, rev) in rows:
        u = db.session.get(User, pid)
        if u is None:
            continue
        prof = getattr(u, 'promoter_profile', None)
        out.append({
            'promoter_id': str(pid),
            'name': u.name,
            'organisation_name': prof.organisation_name if prof else None,
            'photo_url': prof.photo_url if prof else None,
            'completed_purchases_30d': int(count or 0),
            'revenue_30d_usd': str(rev or 0),
        })
    return out
