"""CSV export of attendees per event — per TICKET_GENERATOR_SPEC.md §4.

Two scopes:
    all          — every ticket with a "checked_in" boolean column
    checked_in   — only tickets in 'used' state ("the people who were there")

Columns (per Stage 3 §11.10 default, extends TG's spec):
    short_id, full_id, attendee_name, source,
    ticket_type, price_usd, payment_ref,
    purchase_status, status,
    checked_in (bool), checked_in_at, gateman_name,
    buyer_name, buyer_phone, buyer_email
"""
import csv
import io
from datetime import datetime, timezone

from ..models import Ticket, TicketType


CSV_COLUMNS = [
    'short_id', 'full_id', 'attendee_name', 'source',
    'ticket_type', 'price_usd', 'payment_ref',
    'purchase_status', 'status',
    'checked_in', 'checked_in_at', 'gateman_name',
    'buyer_name', 'buyer_phone', 'buyer_email',
]


def _fmt_dt(dt):
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def attendees_csv(event, scope='all') -> str:
    """Build a CSV string for an event's attendees."""
    q = (Ticket.query
         .join(TicketType, Ticket.ticket_type_id == TicketType.id)
         .filter(TicketType.event_id == event.id))
    if scope == 'checked_in':
        q = q.filter(Ticket.status == 'used')
    tickets = q.order_by(Ticket.created_at.asc()).all()

    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(CSV_COLUMNS)
    for t in tickets:
        row = t.attendees_row()
        writer.writerow([
            row['short_id'],
            row['id'],
            row['attendee_name'],
            row['source'],
            row['ticket_type'] or '',
            row['price_usd'],
            row['payment_ref_full'] or '',
            row['purchase_status'] or '',
            row['status'],
            'true' if row['checked_in'] else 'false',
            row['checked_in_at'] or '',
            row['gateman_name'] or '',
            row['buyer_name'] or '',
            row['buyer_phone'] or '',
            row['buyer_email'] or '',
        ])
    return out.getvalue()


def csv_filename(event, scope='all') -> str:
    """{event-slug}-attendees-{YYYYMMDD}.csv per TG spec §4."""
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    # Simple slug from title (good enough — host has slugify utility too).
    title = (event.title or 'event').lower()
    slug = ''.join(c if c.isalnum() else '-' for c in title)
    slug = '-'.join(filter(None, slug.split('-')))[:60] or 'event'
    if scope == 'checked_in':
        return f"{slug}-checked-in-{today}.csv"
    return f"{slug}-attendees-{today}.csv"
