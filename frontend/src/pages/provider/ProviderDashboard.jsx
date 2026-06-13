// /provider — stats, recent requests with inline accept/decline, today's
// schedule (Stage 4 §6.5).
import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Inbox, CalendarDays, CalendarCheck2, Wrench } from 'lucide-react';
import { providerDashboard } from '../../components/services/api.js';
import { BookingCard } from '../../modules/booking_interface/components/BookingPrimitives.jsx';

function Stat({ icon: Icon, label, value, to }) {
  const body = (
    <div className="card flex items-center gap-3.5 p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[rgb(var(--section-accent)/0.12)]">
        <Icon size={18} className="text-[rgb(var(--section-accent))]" />
      </div>
      <div>
        <p className="text-2xl font-semibold text-ink">{value}</p>
        <p className="text-xs uppercase tracking-wider text-inkm">{label}</p>
      </div>
    </div>
  );
  return to ? <Link to={to} className="block hover:opacity-90">{body}</Link> : body;
}

export default function ProviderDashboard() {
  const [data, setData] = useState(null);

  const load = useCallback(() => {
    providerDashboard().then(setData).catch(() => setData(false));
  }, []);
  useEffect(load, [load]);

  if (data === false) {
    return <div className="card p-8 text-center text-inkm">Could not load your dashboard.</div>;
  }
  if (!data) return <p className="text-sm text-inkm">Loading…</p>;

  const s = data.stats;
  return (
    <div className="space-y-8">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">Dashboard</h1>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Inbox} label="Pending requests" value={s.pending_requests} to="/provider/requests" />
        <Stat icon={CalendarCheck2} label="Today's bookings" value={s.todays_bookings} to="/provider/calendar" />
        <Stat icon={CalendarDays} label="This week" value={s.week_bookings} to="/provider/calendar" />
        <Stat icon={Wrench} label="Active services" value={s.services_active} to="/provider/services" />
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-lg text-ink">Recent requests</h2>
          <Link to="/provider/requests" className="btn-ghost">Open queue →</Link>
        </div>
        {data.recent_requests.length === 0 && (
          <div className="card p-6 text-sm text-inkm">No booking requests yet.</div>
        )}
        <div className="space-y-3">
          {data.recent_requests.map((b) => (
            <BookingCard key={b.id} booking={b} viewerRole="provider" onChanged={load} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg text-ink">Today's schedule</h2>
        {data.todays_calendar.length === 0 && (
          <div className="card p-6 text-sm text-inkm">Nothing confirmed today.</div>
        )}
        <div className="space-y-3">
          {data.todays_calendar.map((b) => (
            <BookingCard key={b.id} booking={b} viewerRole="provider" onChanged={load} />
          ))}
        </div>
      </section>
    </div>
  );
}
