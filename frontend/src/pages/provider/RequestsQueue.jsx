// /provider/requests — pending booking requests with accept / decline /
// WhatsApp, plus a recent-history tab. Conflict (slot_taken) surfaces via
// the action toast and a refetch.
import React, { useCallback, useEffect, useState } from 'react';
import { myBookings } from '../../modules/booking_interface/api.js';
import { BookingCard } from '../../modules/booking_interface/components/BookingPrimitives.jsx';

const TABS = [
  { key: 'requested', label: 'Pending' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: '', label: 'All' },
];

export default function RequestsQueue() {
  const [tab, setTab] = useState('requested');
  const [bookings, setBookings] = useState(null);

  const load = useCallback(() => {
    setBookings(null);
    myBookings({ role: 'provider', status: tab }).then(setBookings)
      .catch(() => setBookings([]));
  }, [tab]);
  useEffect(load, [load]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">Booking requests</h1>
        <p className="mt-1 text-sm text-inkm">
          Accepting locks the slot on your calendar; clashing pending requests are
          auto-declined for you.
        </p>
      </div>
      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-full border px-3.5 py-1.5 text-sm transition ${
              tab === t.key
                ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.15)] text-ink'
                : 'border-bordr bg-bgs text-inkm hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {bookings === null && <p className="text-sm text-inkm">Loading…</p>}
      {bookings && bookings.length === 0 && (
        <div className="card p-8 text-center text-inkm">Nothing here right now.</div>
      )}
      <div className="space-y-3">
        {(bookings || []).map((b) => (
          <BookingCard key={b.id} booking={b} viewerRole="provider" onChanged={load} />
        ))}
      </div>
    </div>
  );
}
