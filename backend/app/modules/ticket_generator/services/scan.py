"""Gate scan validation — per TICKET_GENERATOR_SPEC.md §7.

Pipeline (POST /api/gate/scan):
  1. Split payload on '.' → expect 3 parts.
  2. Recompute HMAC sig; constant-time compare → mismatch = invalid_signature.
  3. Look up ticket by UUID → not found = invalid.
  4. Ticket must belong to gateman's scoped event → else wrong_event.
  5. By status:
        valid    → flip to used; record checkin (result=success).
        used     → return already_used + original checkin info; log duplicate.
        voided   → return voided; log invalid.

First-scan-wins enforced atomically via SELECT … FOR UPDATE on the ticket.
"""
from datetime import datetime, timezone

from extensions import db

from ..models import Ticket, TicketType, Gateman, Checkin
from .qr import verify_payload


def _now():
    return datetime.now(timezone.utc)


def scan_ticket(payload: str, gateman: Gateman, device_id: str = None,
                scanned_at_iso: str = None) -> dict:
    """Validate a scanned QR and persist a checkin row.

    Returns a dict like:
      {
        "result": "valid" | "already_used" | "voided" | "wrong_event" | "invalid_signature" | "invalid",
        "message": "...",
        "ticket": {...} | None,
        "original_checkin": {time, gateman_name, device_id} | None,
      }

    The caller (route) is responsible for db.session.commit().
    """
    # Step 1+2: verify signature & shape.
    tid, ok = verify_payload(payload)
    if not ok:
        # Persist a Checkin row only if the ticket is identifiable (it isn't here).
        # We still want a log line, but no ticket_id to attach to → skip db row.
        return {
            'result': 'invalid_signature',
            'message': 'QR signature failed verification. Possible fake.',
            'ticket': None,
        }

    # Step 3: look up the ticket (with FOR UPDATE for first-scan-wins).
    ticket = (db.session.query(Ticket)
                          .filter(Ticket.id == tid)
                          .with_for_update()
                          .one_or_none())
    if ticket is None:
        return {
            'result': 'invalid',
            'message': 'Ticket not found.',
            'ticket': None,
        }

    # Step 4: scope to gateman's event.
    tt = ticket.ticket_type
    if tt is None or str(tt.event_id) != str(gateman.event_id):
        return {
            'result': 'wrong_event',
            'message': "This ticket is for a different event.",
            'ticket': ticket.buyer_view(),
        }

    # Step 5: dispatch by status.
    if ticket.status == 'voided':
        # log invalid attempt
        db.session.add(Checkin(
            ticket_id=ticket.id,
            gateman_id=gateman.id,
            device_id=device_id,
            scanned_at=_parse_dt(scanned_at_iso) or _now(),
            synced_at=_now(),
            result='invalid',
        ))
        return {
            'result': 'voided',
            'message': 'This ticket was voided. Do not admit.',
            'ticket': ticket.buyer_view(),
        }

    if ticket.status == 'used':
        # Find original checkin for context.
        orig = (db.session.query(Checkin, Gateman)
                            .outerjoin(Gateman, Checkin.gateman_id == Gateman.id)
                            .filter(Checkin.ticket_id == ticket.id,
                                    Checkin.result == 'success')
                            .order_by(Checkin.scanned_at.asc())
                            .first())
        original = None
        if orig:
            c, g = orig
            original = {
                'time': c.scanned_at.isoformat() if c.scanned_at else None,
                'device_id': c.device_id,
                'gateman_name': g.name if g else None,
            }
        elif ticket.checked_in_at:
            original = {
                'time': ticket.checked_in_at.isoformat(),
                'device_id': ticket.checked_in_device,
                'gateman_name': ticket.gateman.name if ticket.gateman else None,
            }
        # Persist a duplicate-result checkin row.
        db.session.add(Checkin(
            ticket_id=ticket.id,
            gateman_id=gateman.id,
            device_id=device_id,
            scanned_at=_parse_dt(scanned_at_iso) or _now(),
            synced_at=_now(),
            result='duplicate',
        ))
        gateman.scan_count = (gateman.scan_count or 0) + 1
        gateman.last_seen_at = _now()
        return {
            'result': 'already_used',
            'message': 'Already scanned.',
            'ticket': ticket.buyer_view(),
            'original_checkin': original,
        }

    # ticket.status == 'valid' → flip to used.
    now = _now()
    ticket.status = 'used'
    ticket.checked_in_at = now
    ticket.checked_in_by = gateman.id
    ticket.checked_in_device = device_id

    db.session.add(Checkin(
        ticket_id=ticket.id,
        gateman_id=gateman.id,
        device_id=device_id,
        scanned_at=_parse_dt(scanned_at_iso) or now,
        synced_at=now,
        result='success',
    ))
    gateman.scan_count = (gateman.scan_count or 0) + 1
    gateman.last_seen_at = now

    return {
        'result': 'valid',
        'message': 'Admit.',
        'ticket': ticket.buyer_view(),
        'scanned_at': now.isoformat(),
    }


def _parse_dt(iso):
    if not iso:
        return None
    try:
        # accept "Z" too
        if iso.endswith('Z'):
            iso = iso[:-1] + '+00:00'
        return datetime.fromisoformat(iso)
    except Exception:
        return None
