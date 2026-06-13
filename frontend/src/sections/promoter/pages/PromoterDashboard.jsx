import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Loader2, Calendar, DollarSign, Users, Clock, Ticket } from 'lucide-react';
import { promoterDashboard } from '../../../modules/ticket_generator/api/index.js';
import { EventCard } from '../../events/components/EventCard.jsx';

function Stat({ icon: Icon, label, value, sub }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <div className="h-9 w-9 rounded-md bg-brand/10 text-brand flex items-center justify-center">
          <Icon size={18} />
        </div>
        <div>
          <div className="text-2xl font-display text-ink">{value}</div>
          <div className="text-[11px] uppercase tracking-wider text-inkm">{label}</div>
          {sub && <div className="text-[11px] text-inkm mt-0.5">{sub}</div>}
        </div>
      </div>
    </div>
  );
}

export default function PromoterDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    promoterDashboard()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
      <Loader2 className="animate-spin" size={16} /> Loading…
    </div>;
  }
  const stats = data?.stats || {};

  return (
    <main className="container-page py-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl text-ink heading-accent">Promoter</h1>
          <p className="text-inkm text-sm mt-1">Manage events, tickets, and the gate.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/promoter/events/new" className="btn-primary">
            <Plus size={14} /> New event
          </Link>
        </div>
      </div>

      <section className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <Stat icon={Calendar} label="Upcoming" value={stats.upcoming_events ?? 0} />
        <Stat icon={Calendar} label="Total events" value={stats.total_events ?? 0} />
        <Stat icon={Ticket} label="Tickets / 30d" value={stats.tickets_sold_30d ?? 0} />
        <Stat icon={DollarSign} label="Revenue / 30d" value={`$${stats.revenue_30d_usd ?? '0.00'}`} />
        <Stat icon={Clock} label="Pending today" value={stats.today_pending_payments ?? 0}
              sub="Buyers awaiting payment confirmation" />
      </section>

      <section className="grid lg:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-lg text-ink">Upcoming events</h2>
            <Link to="/promoter/events" className="text-sm text-inkm hover:text-ink">View all</Link>
          </div>
          {(data?.upcoming_events || []).length === 0 ? (
            <div className="card p-6 text-center text-inkm">No upcoming events.</div>
          ) : (
            <div className="grid gap-3">
              {(data.upcoming_events || []).slice(0, 4).map((e) => (
                <EventCard key={e.id} event={e} to={`/promoter/events/${e.id}`} />
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="font-display text-lg text-ink mb-3">Recent activity</h2>
          <div className="card p-3 max-h-[520px] overflow-y-auto">
            {(data?.recent_purchases || []).length === 0 ? (
              <div className="p-3 text-inkm text-sm">No purchases yet.</div>
            ) : (
              <ul className="divide-y divide-bordr/60">
                {(data.recent_purchases || []).map((r, i) => (
                  <li key={i} className="py-2 text-sm flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <Link to={`/purchases/${r.purchase_id}`} className="text-ink truncate block">
                        #{r.purchase_id.slice(0, 8)} → {r.to_status}
                      </Link>
                      <div className="text-inkm text-[11px]">
                        {r.actor_role} • {r.quantity} ticket{r.quantity === 1 ? '' : 's'} • ${r.total_usd}
                      </div>
                    </div>
                    <span className="text-[11px] text-inkm">
                      {r.created_at ? new Date(r.created_at).toLocaleString('en-ZW', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
