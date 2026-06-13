// /super/booking-disputes — the BookingInterface dispute desk. SEPARATE from
// /super/disputes (PurchaseInterface): different table, different stakes —
// no refunds here, resolution just lands the booking on completed/cancelled.
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { CalendarClock } from 'lucide-react';
import {
  listBookingDisputes, getBookingDispute, resolveBookingDispute,
} from '../../modules/booking_interface/api.js';
import {
  BookingStatusBadge, BookingTimeline, fmtRange,
} from '../../modules/booking_interface/components/BookingPrimitives.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { errMessage } from '../../api/client.js';

export function BookingDisputesInbox() {
  const [status, setStatus] = useState('open');
  const [disputes, setDisputes] = useState(null);

  useEffect(() => {
    setDisputes(null);
    listBookingDisputes(status).then(setDisputes).catch(() => setDisputes([]));
  }, [status]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-2xl text-ink">Booking disputes</h1>
        <p className="mt-1 text-sm text-inkm">
          BookingInterface escalations — separate desk from purchase disputes.
          No money moves on-platform; resolving sets the booking's final state.
        </p>
      </div>
      <div className="flex gap-2">
        {['open', 'resolved', 'all'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={`rounded-full border px-3.5 py-1.5 text-sm capitalize transition ${
              status === s
                ? 'border-brand bg-brand/15 text-ink'
                : 'border-bordr bg-bgs text-inkm hover:text-ink'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      {disputes === null && <p className="text-sm text-inkm">Loading…</p>}
      {disputes && disputes.length === 0 && (
        <div className="card p-8 text-center text-inkm">No {status === 'all' ? '' : status} booking disputes.</div>
      )}
      <div className="space-y-3">
        {(disputes || []).map((d) => (
          <Link key={d.id} to={`/super/booking-disputes/${d.id}`} className="card card-hover block p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <CalendarClock size={15} className="text-brand" />
                  <span className="truncate font-medium text-ink">
                    {d.booking?.label || `Booking ${d.booking_id?.slice(0, 8)}`}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-[10.5px] uppercase tracking-wider ${
                    d.status === 'open'
                      ? 'border-danger/40 bg-danger/10 text-danger'
                      : 'border-success/40 bg-success/10 text-success'
                  }`}>
                    {d.status}
                  </span>
                </div>
                <p className="mt-1 truncate text-sm text-inkm">
                  Raised by {d.raised_by_name} ({d.raised_by_role}) — {d.reason}
                </p>
              </div>
              <span className="text-xs text-inkm">
                {new Date(d.created_at).toLocaleDateString()}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function BookingDisputeDetail() {
  const { disputeId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [dispute, setDispute] = useState(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    getBookingDispute(disputeId).then(setDispute).catch(() => setDispute(false));
  }, [disputeId]);
  useEffect(load, [load]);

  if (dispute === false) {
    return <div className="card p-8 text-center text-inkm">Dispute not found.</div>;
  }
  if (!dispute) return <p className="text-sm text-inkm">Loading…</p>;

  const booking = dispute.booking;

  const resolve = async (resolution) => {
    setBusy(true);
    try {
      await resolveBookingDispute(disputeId, resolution, note.trim() || undefined);
      toast.success(`Dispute resolved — booking ${resolution}.`);
      navigate('/super/booking-disputes');
    } catch (err) {
      toast.error(errMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link to="/super/booking-disputes" className="text-sm text-inkm hover:text-ink">
        ← Booking disputes
      </Link>
      <div className="card space-y-3 p-5">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="font-display text-xl text-ink">{booking?.label || 'Booking'}</h1>
          {booking && <BookingStatusBadge status={booking.status} />}
        </div>
        {booking && <p className="text-sm text-inkm">{fmtRange(booking)} · {booking.duration_hours}h</p>}
        <div className="grid gap-2 border-t border-bordr pt-3 text-sm sm:grid-cols-2">
          <p><span className="text-inkm">Requester:</span> <span className="text-ink">{booking?.requester?.name}</span></p>
          <p><span className="text-inkm">Provider:</span> <span className="text-ink">{booking?.provider?.name}</span></p>
          <p><span className="text-inkm">Raised by:</span> <span className="text-ink">{dispute.raised_by_name} ({dispute.raised_by_role})</span></p>
          <p><span className="text-inkm">Opened:</span> <span className="text-ink">{new Date(dispute.created_at).toLocaleString()}</span></p>
        </div>
        <div>
          <span className="text-sm text-inkm">Reason</span>
          <p className="mt-1 rounded-md border border-bordr bg-bgs2 p-3 text-sm text-ink">{dispute.reason}</p>
        </div>
      </div>

      {dispute.status === 'open' ? (
        <div className="card space-y-4 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wider text-inkm">Resolve</h2>
          <p className="text-sm text-inkm">
            Mark the booking <strong className="text-ink">completed</strong> (the work happened)
            or <strong className="text-ink">cancelled</strong> (it didn't). Both parties are notified;
            no money moves through ZimHub.
          </p>
          <Textarea
            label="Resolution note (optional)"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className="flex gap-2">
            <Button loading={busy} onClick={() => resolve('completed')}>Resolve → completed</Button>
            <Button variant="secondary" loading={busy} onClick={() => resolve('cancelled')}>
              Resolve → cancelled
            </Button>
          </div>
        </div>
      ) : (
        <div className="card p-5 text-sm">
          <p className="text-ink">
            Resolved → <strong>{dispute.resolution}</strong>
            {dispute.resolved_at && (
              <span className="text-inkm"> on {new Date(dispute.resolved_at).toLocaleString()}</span>
            )}
          </p>
          {dispute.resolution_note && <p className="mt-2 text-inkm">{dispute.resolution_note}</p>}
        </div>
      )}

      {booking?.events && (
        <div className="card p-5">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-wider text-inkm">Booking history</h2>
          <BookingTimeline events={booking.events} />
        </div>
      )}
    </div>
  );
}
