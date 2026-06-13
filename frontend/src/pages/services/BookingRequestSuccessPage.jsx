// /services/booking/:id/success — explicit "request sent, NOT yet confirmed"
// confirmation (Stage 4 §6.4) with links to My bookings.
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Hourglass } from 'lucide-react';
import { getBooking } from '../../modules/booking_interface/api.js';
import { fmtRange, BookingStatusBadge } from '../../modules/booking_interface/components/BookingPrimitives.jsx';

export default function BookingRequestSuccessPage() {
  const { id } = useParams();
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    getBooking(id).then(setBooking).catch(() => setBooking(false));
  }, [id]);

  return (
    <div className="mx-auto max-w-lg">
      <div className="card p-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-[rgb(var(--section-accent)/0.5)] bg-[rgb(var(--section-accent)/0.12)]">
          <Hourglass className="text-[rgb(var(--section-accent))]" />
        </div>
        <h1 className="font-display text-2xl text-ink">Request sent</h1>
        <p className="mt-2 text-inkm">
          Your booking is <strong className="text-ink">awaiting the provider's response</strong> —
          it isn't confirmed yet. We'll notify you the moment they reply.
        </p>
        {booking && (
          <div className="mt-5 rounded-lg border border-bordr bg-bgs2 p-4 text-left text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-ink">{booking.label || 'Booking'}</span>
              <BookingStatusBadge status={booking.status} />
            </div>
            <p className="mt-1 text-inkm">{fmtRange(booking)}</p>
            {booking.quoted_rate_usd != null ? (
              <p className="mt-1 text-inkm">Estimated: ${booking.quoted_rate_usd}</p>
            ) : (
              <p className="mt-1 text-inkm">Billed by distance — agree directly with your provider.</p>
            )}
          </div>
        )}
        {booking === false && (
          <p className="mt-4 text-sm text-inkm">Booking details unavailable — find it under My bookings.</p>
        )}
        <div className="mt-6 flex justify-center gap-3">
          <Link to="/my/bookings" className="btn-primary">My bookings</Link>
          <Link to="/services" className="btn-secondary">Back to Services</Link>
        </div>
      </div>
    </div>
  );
}
