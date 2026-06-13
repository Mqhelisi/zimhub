"""TicketHandler — `listing_type='event_ticket'` for PurchaseInterface.

Per TICKET_GENERATOR_SPEC.md §10 and STAGE_3_SPEC.md §5.4.

KEY DESIGN POINTS:
  - One Purchase per ticket_type (listing_id == ticket_type_id).
  - `Purchase.quantity` == number of tickets in the Purchase. Each ticket gets
    a distinct row in `tickets` minted on on_payment_confirmed.
  - `domain_payload` shape (per Stage 3 §5.4 + TG §1):
        {
          "attendee_names": ["Name 1", "Name 2", ...],   # len == quantity
          "buyer_name_at_purchase": "...",                # snapshot
          "buyer_phone_at_purchase": "+263..."            # snapshot
        }
  - SELECT … FOR UPDATE on the ticket_types row in on_initiate prevents
    last-ticket races; the loser gets PurchaseHandlerError('sold_out').
  - Ticket validity is DECOUPLED from settlement (TG §1) — minted at
    on_payment_confirmed, status='valid' immediately, scannable from there.
  - Flyer events: ticket_types should never exist for them, so a flyer event
    can't be reached here. Defensive checks anyway.
"""
import logging
from decimal import Decimal
from uuid import UUID as _UUID

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from app.services import host
from app.modules.purchase_interface.handlers import PurchaseHandlerError

from ..models import Event, TicketType, Ticket
from .qr import sign_payload


log = logging.getLogger('zimhub.ticket_generator.handler')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _coerce_uuid(v):
    if isinstance(v, _UUID):
        return v
    return _UUID(str(v))


def _validate_attendee_names(domain_payload, quantity):
    names = (domain_payload or {}).get('attendee_names') or []
    if not isinstance(names, list):
        raise PurchaseHandlerError(
            'invalid_payload', 'attendee_names must be a list.',
        )
    cleaned = [str(n).strip()[:80] for n in names]
    cleaned = [n for n in cleaned if n]  # drop empty
    if len(cleaned) != int(quantity):
        raise PurchaseHandlerError(
            'invalid_payload',
            f'Each ticket needs an attendee name (got {len(cleaned)}, need {quantity}).',
        )
    return cleaned


# ---------------------------------------------------------------------------
# Notifications — TG-specific kinds
# ---------------------------------------------------------------------------
def _notify_tickets_delivered(purchase, ticket_records, event, ticket_type):
    """Fire mock SMS + WhatsApp + in-app to the buyer (TG spec §10)."""
    buyer = purchase.buyer
    if buyer is None:
        return
    n_tix = len(ticket_records)
    body = (
        f"ZimHub: {n_tix} ticket{'s' if n_tix != 1 else ''} for "
        f"{event.title} ({ticket_type.name}) are now valid and scannable. "
        f"Open My Tickets to view your QR codes."
    )
    host.notify(
        buyer.id, 'event_ticket_issued',
        f"Tickets issued: {event.title}",
        f"{n_tix} ticket{'s' if n_tix != 1 else ''} for {event.title} — "
        f"{ticket_type.name}. Open My Tickets to view QRs.",
        metadata={
            'purchase_id': str(purchase.id),
            'event_id': str(event.id),
            'ticket_ids': [str(t.id) for t in ticket_records],
        },
    )
    # Mock SMS + WhatsApp (TG spec §13).
    host.send(channel='sms', recipient=buyer.phone, body=body)
    host.send(channel='whatsapp', recipient=buyer.phone, body=body)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------
class TicketHandler:
    """Plugged into PurchaseInterface registry under listing_type='event_ticket'."""
    LISTING_TYPE = 'event_ticket'
    SELLER_CAPABILITY = 'is_promoter'

    # ------------------------------------------------------------------
    # resolve_listing — discover seller/price/availability. Read-only.
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_listing(listing_id, qty=1, domain_payload=None):
        try:
            tt_id = _coerce_uuid(listing_id)
        except (ValueError, TypeError):
            raise PurchaseHandlerError(
                'invalid_listing', 'Bad ticket_type_id.',
            )
        tt = db.session.get(TicketType, tt_id)
        if tt is None:
            raise PurchaseHandlerError(
                'unknown_listing', 'Ticket type not found.',
            )
        event = tt.event
        if event is None:
            raise PurchaseHandlerError(
                'unknown_listing', 'Event not found.',
            )
        # Defensive: tickets only sell for ticketed events.
        if event.mode != 'ticketed':
            raise PurchaseHandlerError(
                'wrong_mode',
                'This is a flyer event — no tickets to sell.',
            )
        # Status must be active (not draft / cancelled / archived).
        if event.status != 'active':
            raise PurchaseHandlerError(
                'event_not_active',
                f"Event is {event.status}; tickets unavailable.",
            )
        # Cap: MAX_PER_PURCHASE
        max_per = int(host.config('MAX_PER_PURCHASE', 10) or 10)
        if int(qty) > max_per:
            raise PurchaseHandlerError(
                'too_many_tickets',
                f'Maximum {max_per} tickets per purchase.',
            )
        remaining = tt.quantity_remaining
        quantity_available = remaining if remaining >= int(qty) else 0
        return {
            'seller_id': event.promoter_id,
            'unit_price_usd': Decimal(str(tt.price_usd)),
            'currency': 'USD',
            'quantity_available': quantity_available,
            'label': f"{event.title} — {tt.name}",
        }

    # ------------------------------------------------------------------
    # on_initiate — race-safe hold via SELECT … FOR UPDATE.
    # ------------------------------------------------------------------
    @staticmethod
    def on_initiate(purchase, domain_payload):
        tt_id = _coerce_uuid(purchase.listing_id)
        # Lock the ticket_types row.
        tt = (db.session.query(TicketType)
                        .filter(TicketType.id == tt_id)
                        .with_for_update()
                        .one_or_none())
        if tt is None:
            raise PurchaseHandlerError('unknown_listing', 'Ticket type not found.')

        event = tt.event
        if event is None or event.mode != 'ticketed':
            raise PurchaseHandlerError(
                'wrong_mode', 'Cannot reserve tickets on a flyer event.',
            )
        if event.status != 'active':
            raise PurchaseHandlerError(
                'event_not_active', f"Event is {event.status}.",
            )

        # Validate attendee names (one per ticket).
        cleaned_names = _validate_attendee_names(domain_payload, purchase.quantity)

        if tt.quantity_remaining < purchase.quantity:
            raise PurchaseHandlerError(
                'sold_out',
                f"'{tt.name}' has only {max(0, tt.quantity_remaining)} left.",
            )

        tt.quantity_held = (tt.quantity_held or 0) + int(purchase.quantity)

        # Snapshot cleaned names + price into the payload so post-confirm doesn't
        # have to revalidate.
        new_payload = dict(domain_payload or {})
        new_payload['attendee_names'] = cleaned_names
        new_payload['unit_price_usd_at_checkout'] = str(tt.price_usd)
        new_payload['ticket_type_id'] = str(tt.id)
        new_payload['event_id'] = str(event.id)
        purchase.domain_payload = new_payload

    # ------------------------------------------------------------------
    # on_payment_confirmed — mint one ticket per attendee, deliver QR.
    # ------------------------------------------------------------------
    @staticmethod
    def on_payment_confirmed(purchase, domain_payload):
        tt_id = _coerce_uuid(purchase.listing_id)
        tt = (db.session.query(TicketType)
                        .filter(TicketType.id == tt_id)
                        .with_for_update()
                        .one_or_none())
        if tt is None:
            raise PurchaseHandlerError(
                'unknown_listing',
                'Ticket type no longer exists.',
            )
        event = tt.event
        if event is None:
            raise PurchaseHandlerError('unknown_listing', 'Event not found.')

        names = (domain_payload or {}).get('attendee_names') or []
        if len(names) != int(purchase.quantity):
            # Should never happen because on_initiate validated, but defend.
            raise PurchaseHandlerError(
                'invalid_payload',
                'Attendee names changed; expected exactly quantity entries.',
            )

        snapshot_price = Decimal(str(tt.price_usd))

        # Strip the payment_ref for storage on each ticket (mirror Purchase's).
        pref = (purchase.payment_ref or '').strip() or None

        minted = []
        for name in names:
            t = Ticket(
                ticket_type_id=tt.id,
                purchase_id=purchase.id,
                attendee_name=name[:80],
                source='online',
                price_usd=snapshot_price,
                payment_ref=pref,
                qr_code='placeholder',  # patched after we have the id
                status='valid',
            )
            db.session.add(t)
            db.session.flush()  # populate t.id
            t.qr_code = sign_payload(str(t.id))
            minted.append(t)

        # Move inventory: held → sold.
        qty = int(purchase.quantity)
        tt.quantity_held = max(0, (tt.quantity_held or 0) - qty)
        tt.quantity_sold = (tt.quantity_sold or 0) + qty

        # Deliver via mock SMS + WhatsApp + in-app.
        _notify_tickets_delivered(purchase, minted, event, tt)

        return {'refs': {
            'ticket_ids': [str(t.id) for t in minted],
            'ticket_count': len(minted),
        }}

    # ------------------------------------------------------------------
    # on_cancel — release the hold.
    # ------------------------------------------------------------------
    @staticmethod
    def on_cancel(purchase, domain_payload):
        tt_id = _coerce_uuid(purchase.listing_id)
        tt = (db.session.query(TicketType)
                        .filter(TicketType.id == tt_id)
                        .with_for_update()
                        .one_or_none())
        if tt is None:
            return  # nothing to release
        qty = int(purchase.quantity)
        tt.quantity_held = max(0, (tt.quantity_held or 0) - qty)

    # ------------------------------------------------------------------
    # on_complete — no-op for tickets (TG spec §10).
    # ------------------------------------------------------------------
    @staticmethod
    def on_complete(purchase, domain_payload):
        return None

    # ------------------------------------------------------------------
    # on_dispute_resolution — void linked tickets on refund/cancel.
    # ------------------------------------------------------------------
    @staticmethod
    def on_dispute_resolution(purchase, resolution, domain_payload):
        if resolution == 'completed':
            return
        if resolution not in ('refunded', 'cancelled'):
            return

        # Find all minted tickets for this purchase and void them; reverse stock.
        tickets = (db.session.query(Ticket)
                              .filter(Ticket.purchase_id == purchase.id)
                              .all())
        if not tickets:
            # Tickets were never minted (dispute happened pre-confirmation) →
            # just release the hold.
            tt_id = _coerce_uuid(purchase.listing_id)
            tt = db.session.get(TicketType, tt_id)
            if tt is not None:
                qty = int(purchase.quantity)
                tt.quantity_held = max(0, (tt.quantity_held or 0) - qty)
            return

        ticket_type_ids = {t.ticket_type_id for t in tickets}
        # Group qty by ticket_type for inventory reversal.
        per_type = {}
        for t in tickets:
            # Only valid/used flow into the sold bucket; voided already returned.
            if t.status == 'voided':
                continue
            per_type[t.ticket_type_id] = per_type.get(t.ticket_type_id, 0) + 1

        # Void each ticket
        for t in tickets:
            if t.status != 'voided':
                t.status = 'voided'

        # Reverse the sold count by per_type qty.
        for tt_id, n in per_type.items():
            tt = (db.session.query(TicketType)
                            .filter(TicketType.id == tt_id)
                            .with_for_update()
                            .one_or_none())
            if tt is None:
                continue
            tt.quantity_sold = max(0, (tt.quantity_sold or 0) - n)

        # Notify the buyer their tickets were voided.
        buyer = purchase.buyer
        if buyer is not None:
            host.notify(
                buyer.id, 'event_tickets_voided',
                'Tickets voided',
                f'Your {len(tickets)} ticket(s) for this purchase were voided '
                f'because the dispute was resolved as {resolution}.',
                metadata={'purchase_id': str(purchase.id)},
            )
