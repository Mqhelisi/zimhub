// /my/bookings — buyer's bookings with All / Upcoming / Past / Cancelled
// filters (Stage 4 §6.6). Off-platform payment note included.
import React, { useCallback, useEffect, useState } from 'react';
import { myBookings } from '../../modules/booking_interface/api.js';
import { BookingCard } from '../../modules/booking_interface/components/BookingPrimitives.jsx';

const FILTERS = ['All', 'Upcoming', 'Past', 'Cancelled'];

function bucket(b) {
  const now = new Date();
  if (['cancelled', 'declined', 'expired'].includes(b.status)) return 'Cancelled';
  if (['completed', 'no_show'].includes(b.status)) return 'Past';
  if (new Date(b.end_at) < now && b.status !== 'requested' && b.status !== 'confirmed') return 'Past';
  return new Date(b.start_at) >= now || ['requested', 'confirmed', 'disputed'].includes(b.status)
    ? 'Upcoming' : 'Past';
}

export default function BuyerBookingsPage() {
  const [bookings, setBookings] = useState(null);
  const [filter, setFilter] = useState('All');

  const load = useCallback(() => {
    myBookings({ role: 'requester' }).then(setBookings).catch(() => setBookings([]));
  }, []);
  useEffect(load, [load]);

  const visible = (bookings || []).filter(
    (b) => filter === 'All' || bucket(b) === filter,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">My bookings</h1>
        <p className="mt-1 text-sm text-inkm">
          Requests and confirmed time with your providers. Payment is settled directly
          with the provider — ZimHub never holds money for bookings.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
              filter === f
                ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.15)] text-ink'
                : 'border-bordr bg-bgs text-inkm hover:text-ink'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {bookings === null && <p className="text-sm text-inkm">Loading…</p>}
      {bookings && visible.length === 0 && (
        <div className="card p-8 text-center text-inkm">
          Nothing here yet — browse <a href="/services" className="text-brand">Services</a> to
          request your first booking.
        </div>
      )}
      <div className="space-y-3">
        {visible.map((b) => (
          <BookingCard
            key={b.id}
            booking={b}
            viewerRole="requester"
            linkTo={`/my/bookings/${b.id}`}
            onChanged={load}
          />
        ))}
      </div>
    </div>
  );
}
