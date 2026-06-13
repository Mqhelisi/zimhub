// BookingInterface UI primitives — status badge, timeline, role-aware
// actions, and the list-row card. Embedded by Stage 4's buyer / provider /
// super pages so booking state renders identically everywhere.
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarClock, Check, X, MessageCircle, AlertTriangle, Ban, UserX,
  CheckCircle2, Clock,
} from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { Modal } from '../../../components/ui/Modal.jsx';
import { Textarea } from '../../../components/ui/Textarea.jsx';
import { errMessage } from '../../../api/client.js';
import * as biApi from '../api.js';

// ---------------------------------------------------------------------------
export const STATUS_META = {
  requested: { label: 'Awaiting response', cls: 'border-warning/40 bg-warning/10 text-warning' },
  confirmed: { label: 'Confirmed', cls: 'border-[rgb(var(--section-accent)/0.5)] bg-[rgb(var(--section-accent)/0.12)] text-[rgb(var(--section-accent))]' },
  declined: { label: 'Declined', cls: 'border-bordr bg-bgs2 text-inkm' },
  cancelled: { label: 'Cancelled', cls: 'border-bordr bg-bgs2 text-inkm' },
  expired: { label: 'Expired', cls: 'border-bordr bg-bgs2 text-inkm' },
  completed: { label: 'Completed', cls: 'trust-badge' },
  no_show: { label: 'No-show', cls: 'border-danger/40 bg-danger/10 text-danger' },
  disputed: { label: 'Disputed', cls: 'border-danger/40 bg-danger/10 text-danger' },
};

export function BookingStatusBadge({ status, className = '' }) {
  const meta = STATUS_META[status] || { label: status, cls: 'border-bordr bg-bgs2 text-inkm' };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wider ${meta.cls} ${className}`}>
      {meta.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
export function fmtRange(b) {
  const s = new Date(b.start_at);
  const e = new Date(b.end_at);
  const date = s.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' });
  const t = (d) => d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  return `${date}, ${t(s)} – ${t(e)}`;
}

// ---------------------------------------------------------------------------
export function BookingTimeline({ events = [] }) {
  if (!events.length) return null;
  return (
    <ol className="space-y-2">
      {events.map((ev) => (
        <li key={ev.id} className="flex items-start gap-2.5 text-sm">
          <Clock size={14} className="mt-0.5 shrink-0 text-inkm" />
          <div>
            <span className="text-ink">
              {ev.from_status ? `${ev.from_status} → ` : ''}{ev.to_status}
            </span>
            <span className="ml-2 text-xs text-inkm">
              {ev.actor_role}{ev.note ? ` — ${ev.note}` : ''} · {new Date(ev.created_at).toLocaleString()}
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------
export function WhatsAppButton({ bookingId, className = '' }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant="secondary"
      loading={busy}
      className={className}
      onClick={async () => {
        setBusy(true);
        try {
          const url = await biApi.whatsappLink(bookingId);
          window.open(url, '_blank', 'noopener');
        } catch (err) {
          toast.error(errMessage(err));
        } finally {
          setBusy(false);
        }
      }}
    >
      <MessageCircle size={15} /> WhatsApp
    </Button>
  );
}

// ---------------------------------------------------------------------------
function ReasonModal({ open, title, cta, onClose, onSubmit, required = false }) {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <Textarea
        label={required ? 'Reason (required)' : 'Reason (optional)'}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={3}
        placeholder="Add a short note for the other party…"
      />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Back</Button>
        <Button
          loading={busy}
          disabled={required && !reason.trim()}
          onClick={async () => {
            setBusy(true);
            try { await onSubmit(reason.trim()); onClose(); }
            finally { setBusy(false); }
          }}
        >
          {cta}
        </Button>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Role-aware actions — renders only what `permitted_actions` allows, so the
// backend stays the single source of truth on legality.
export function BookingActions({ booking, onChanged, compact = false }) {
  const toast = useToast();
  const [modal, setModal] = useState(null); // 'decline' | 'cancel' | 'dispute'
  const [busy, setBusy] = useState(false);
  const actions = booking.permitted_actions || [];

  const run = async (fn, success) => {
    setBusy(true);
    try {
      const updated = await fn();
      toast.success(success);
      onChanged?.(updated);
    } catch (err) {
      toast.error(errMessage(err));
      onChanged?.(); // refetch — state may have moved (e.g. slot_taken)
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`flex flex-wrap items-center gap-2 ${compact ? '' : 'mt-2'}`}>
      {actions.includes('accept') && (
        <Button loading={busy} onClick={() => run(() => biApi.acceptBooking(booking.id), 'Booking confirmed.')}>
          <Check size={15} /> Confirm
        </Button>
      )}
      {actions.includes('decline') && (
        <Button variant="secondary" onClick={() => setModal('decline')}>
          <X size={15} /> Decline
        </Button>
      )}
      {actions.includes('cancel') && (
        <Button variant="secondary" onClick={() => setModal('cancel')}>
          <Ban size={15} /> Cancel
        </Button>
      )}
      {actions.includes('no_show') && (
        <Button variant="danger" loading={busy}
          onClick={() => run(() => biApi.markNoShow(booking.id), 'Flagged as no-show.')}>
          <UserX size={15} /> No-show
        </Button>
      )}
      {booking.status === 'confirmed' && new Date(booking.end_at) < new Date() && (
        <Button loading={busy}
          onClick={() => run(() => biApi.markComplete(booking.id), 'Marked complete.')}>
          <CheckCircle2 size={15} /> Mark complete
        </Button>
      )}
      {actions.includes('dispute') && (
        <Button variant="ghost" onClick={() => setModal('dispute')}>
          <AlertTriangle size={15} /> Dispute
        </Button>
      )}
      {actions.includes('whatsapp') && <WhatsAppButton bookingId={booking.id} />}

      <ReasonModal
        open={modal === 'decline'} title="Decline this request" cta="Decline"
        onClose={() => setModal(null)}
        onSubmit={(reason) => run(() => biApi.declineBooking(booking.id, reason), 'Request declined.')}
      />
      <ReasonModal
        open={modal === 'cancel'} title="Cancel this booking" cta="Cancel booking"
        onClose={() => setModal(null)}
        onSubmit={(reason) => run(() => biApi.cancelBooking(booking.id, reason), 'Booking cancelled.')}
      />
      <ReasonModal
        open={modal === 'dispute'} title="Raise a dispute" cta="Raise dispute" required
        onClose={() => setModal(null)}
        onSubmit={(reason) => run(async () => {
          const { booking: b } = await biApi.raiseDispute(booking.id, reason);
          return b;
        }, 'Dispute raised — an admin will review it.')}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// List-row card — used by buyer "My bookings" and the provider requests queue.
export function BookingCard({ booking, viewerRole = 'requester', linkTo, onChanged }) {
  const counterparty = viewerRole === 'requester' ? booking.provider : booking.requester;
  const header = (
    <>
      <div className="flex items-center gap-2">
        <CalendarClock size={16} className="shrink-0 text-[rgb(var(--section-accent))]" />
        <span className="truncate font-medium text-ink">{booking.label || 'Booking'}</span>
        <BookingStatusBadge status={booking.status} />
      </div>
      <p className="mt-1 text-sm text-inkm">
        {fmtRange(booking)}
        {counterparty?.name ? ` · with ${counterparty.name}` : ''}
        {booking.quoted_rate_usd != null
          ? ` · est. $${booking.quoted_rate_usd}`
          : (booking.domain_payload?.distance_km != null
            ? ` · ${booking.domain_payload.distance_km} km — by distance`
            : '')}
      </p>
    </>
  );
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          {linkTo ? <Link to={linkTo} className="block hover:opacity-90">{header}</Link> : header}
        </div>
        <BookingActions booking={booking} onChanged={onChanged} compact />
      </div>
    </div>
  );
}
