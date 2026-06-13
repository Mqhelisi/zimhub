// /my/bookings/:id — full booking detail: status, parties, timeline,
// permitted actions, WhatsApp hand-off, dispute banner.
import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { getBooking } from '../../modules/booking_interface/api.js';
import {
  BookingStatusBadge, BookingTimeline, BookingActions, fmtRange,
} from '../../modules/booking_interface/components/BookingPrimitives.jsx';

export default function BuyerBookingDetailPage() {
  const { id } = useParams();
  const [booking, setBooking] = useState(null);
  const [missing, setMissing] = useState(false);

  const load = useCallback(() => {
    getBooking(id).then(setBooking).catch(() => setMissing(true));
  }, [id]);
  useEffect(load, [load]);

  if (missing) {
    return (
      <div className="card p-8 text-center text-inkm">
        Booking not found. <Link to="/my/bookings" className="text-brand">Back to my bookings →</Link>
      </div>
    );
  }
  if (!booking) return <p className="text-sm text-inkm">Loading…</p>;

  const openDispute = (booking.disputes || []).find((d) => d.status === 'open');

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link to="/my/bookings" className="text-sm text-inkm hover:text-ink">← My bookings</Link>
        <div className="mt-2 flex flex-wrap items-center gap-2.5">
          <h1 className="font-display text-2xl text-ink">{booking.label || 'Booking'}</h1>
          <BookingStatusBadge status={booking.status} />
        </div>
        <p className="mt-1 text-inkm">{fmtRange(booking)} · {booking.duration_hours}h</p>
      </div>

      {openDispute && (
        <div className="flex items-start gap-2.5 rounded-lg border border-danger/40 bg-danger/10 p-3.5 text-sm">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-danger" />
          <div>
            <p className="font-medium text-danger">Dispute open</p>
            <p className="text-inkm">{openDispute.reason} — an admin will review and resolve this.</p>
          </div>
        </div>
      )}

      <div className="card space-y-3 p-5 text-sm">
        <div className="flex justify-between gap-3">
          <span className="text-inkm">Provider</span>
          <span className="text-ink">{booking.provider?.name}</span>
        </div>
        {booking.quoted_rate_usd != null ? (
          <div className="flex justify-between gap-3">
            <span className="text-inkm">Estimated rate</span>
            <span className="text-ink">${booking.quoted_rate_usd} <span className="text-xs text-inkm">(indicative)</span></span>
          </div>
        ) : (
          <div className="flex justify-between gap-3">
            <span className="text-inkm">Pricing</span>
            <span className="text-ink">Billed by distance — agree directly</span>
          </div>
        )}
        {booking.domain_payload?.distance_km != null && (
          <div className="flex justify-between gap-3">
            <span className="text-inkm">Distance</span>
            <span className="text-ink">{booking.domain_payload.distance_km} km</span>
          </div>
        )}
        {booking.message && (
          <div>
            <span className="text-inkm">Your notes</span>
            <p className="mt-1 rounded-md border border-bordr bg-bgs2 p-2.5 text-ink">{booking.message}</p>
          </div>
        )}
        <p className="border-t border-bordr pt-3 text-xs text-inkm">
          Payment happens directly between you and the provider — coordinate over WhatsApp.
        </p>
      </div>

      <BookingActions booking={booking} onChanged={load} />

      <div className="card p-5">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wider text-inkm">History</h2>
        <BookingTimeline events={booking.events} />
      </div>
    </div>
  );
}
