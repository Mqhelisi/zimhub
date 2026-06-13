"""Buyer-facing ticket endpoints — per TG spec §9 (Buyer)."""
import io
import logging

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.utils.decorators import require_auth
from app.utils.errors import not_found, forbidden, error_response
from app.services import host

from ..models import Ticket, TicketType, Event
from app.modules.purchase_interface.models import Purchase


log = logging.getLogger('zimhub.ticket_generator.tickets')

tickets_bp = Blueprint('tg_tickets', __name__, url_prefix='/api')


def _viewer_owns_ticket(ticket, user) -> bool:
    if user is None or ticket is None:
        return False
    if getattr(user, 'is_super_admin', False):
        return True
    if ticket.purchase and str(ticket.purchase.buyer_id) == str(user.id):
        return True
    # Promoter of the event may also view (e.g. for attendee detail).
    if ticket.ticket_type and ticket.ticket_type.event and \
       str(ticket.ticket_type.event.promoter_id) == str(user.id):
        return True
    return False


@tickets_bp.get('/my/tickets')
@require_auth
def my_tickets(user):
    """All tickets where the current user is the buyer of the linked Purchase."""
    rows = (db.session.query(Ticket)
            .join(Purchase, Ticket.purchase_id == Purchase.id)
            .filter(Purchase.buyer_id == user.id)
            .order_by(Ticket.created_at.desc())
            .all())
    return jsonify({'tickets': [t.buyer_view() for t in rows]})


@tickets_bp.get('/tickets/<ticket_id>')
@require_auth
def ticket_detail(user, ticket_id):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        return not_found('Ticket not found.')
    if not _viewer_owns_ticket(t, user):
        return forbidden('You do not have access to this ticket.')
    return jsonify({'ticket': t.buyer_view()})


@tickets_bp.get('/tickets/<ticket_id>/qr.png')
@require_auth
def ticket_qr_png(user, ticket_id):
    """Server-side QR PNG (printing / handoff). Not the primary render path —
    buyer-facing UI renders the QR client-side from `qr_code` for portability.
    """
    t = db.session.get(Ticket, ticket_id)
    if not t:
        return not_found('Ticket not found.')
    if not _viewer_owns_ticket(t, user):
        return forbidden('You do not have access to this ticket.')

    try:
        import qrcode
    except ImportError:
        return error_response(
            'qr_library_missing',
            'Server-side QR rendering requires the `qrcode` package.',
            500,
        )
    img = qrcode.make(t.qr_code)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png',
                     download_name=f'ticket-{str(t.id)[:8]}.png')


@tickets_bp.post('/tickets/<ticket_id>/resend')
@require_auth
def ticket_resend(user, ticket_id):
    t = db.session.get(Ticket, ticket_id)
    if not t:
        return not_found('Ticket not found.')
    if not _viewer_owns_ticket(t, user):
        return forbidden('You do not have access to this ticket.')

    buyer = t.purchase.buyer if t.purchase else None
    if not buyer:
        return error_response('no_buyer', 'This ticket has no online buyer to notify.', 400)

    ev = t.ticket_type.event if t.ticket_type else None
    body = (
        f"ZimHub: Your ticket for {ev.title if ev else 'the event'} is valid. "
        f"Open My Tickets in ZimHub to view the QR. Attendee: {t.attendee_name}."
    )
    try:
        host.send(channel='sms', recipient=buyer.phone, body=body)
        host.send(channel='whatsapp', recipient=buyer.phone, body=body)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.exception('Could not resend ticket %s', ticket_id)
        return error_response('server_error', 'Resend failed.', 500)
    return jsonify({'ok': True})
