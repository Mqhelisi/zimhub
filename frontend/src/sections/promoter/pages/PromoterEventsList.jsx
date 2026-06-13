import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Loader2 } from 'lucide-react';
import { EventCard } from '../../events/components/EventCard.jsx';
import { promoterListEvents } from '../../../modules/ticket_generator/api/index.js';

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'draft', label: 'Drafts' },
  { value: 'pending_approval', label: 'Pending' },
  { value: 'cancelled', label: 'Cancelled' },
];

export default function PromoterEventsList() {
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState('');
  const [mode, setMode] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    promoterListEvents({ status: filter, mode })
      .then((r) => setEvents(r.events || []))
      .finally(() => setLoading(false));
  }, [filter, mode]);

  return (
    <main className="container-page py-8 space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="font-display text-3xl text-ink heading-accent">My events</h1>
        <Link to="/promoter/events/new" className="btn-primary"><Plus size={14} /> New event</Link>
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        {FILTERS.map((f) => (
          <button key={f.value} type="button"
            onClick={() => setFilter(f.value)}
            className={`pill ${filter === f.value ? '!bg-brand !text-bg !border-brand' : ''}`}>
            {f.label}
          </button>
        ))}
        <span className="text-inkm text-xs ml-2">|</span>
        <select className="input-base !py-1.5 !w-auto" value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="">All formats</option>
          <option value="ticketed">Ticketed</option>
          <option value="flyer">Flyer</option>
        </select>
      </div>

      {loading ? (
        <div className="text-inkm flex items-center gap-2 py-12 justify-center">
          <Loader2 className="animate-spin" size={16} /> Loading…
        </div>
      ) : events.length === 0 ? (
        <div className="card p-8 text-center text-inkm">
          No events match. <Link to="/promoter/events/new" className="text-brand">Create one</Link>.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map((e) => <EventCard key={e.id} event={e} to={`/promoter/events/${e.id}`} />)}
        </div>
      )}
    </main>
  );
}
