import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Loader2 } from 'lucide-react';
import { EventCard } from '../components/EventCard.jsx';
import { listEvents, listCategories, topRanking } from '../../../modules/ticket_generator/api/index.js';

export default function EventsHome() {
  const [events, setEvents] = useState([]);
  const [categories, setCategories] = useState([]);
  const [top, setTop] = useState({ top_events: [], top_promoters: [] });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ category: '', mode: 'all', timing: 'upcoming', q: '' });

  useEffect(() => {
    listCategories().then((r) => setCategories(r.categories || [])).catch(() => {});
    topRanking().then(setTop).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listEvents(filters)
      .then((r) => { if (!cancelled) setEvents(r.events || []); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters.category, filters.mode, filters.timing, filters.q]);

  const upcoming = useMemo(() => events.filter((e) => !e.is_past), [events]);
  const past = useMemo(() => events.filter((e) => e.is_past), [events]);

  return (
    <main className="container-page py-8 space-y-8">
      <section className="events-hero rounded-2xl border border-bordr p-6 sm:p-10">
        <div className="max-w-2xl">
          <span className="pill mode-pill-ticketed">Events in Bulawayo & beyond</span>
          <h1 className="mt-3 font-display text-3xl sm:text-4xl text-ink heading-accent">
            What's on tonight
          </h1>
          <p className="mt-3 text-inkm max-w-xl">
            Live shows, gospel nights, comedy, festivals — buy tickets or RSVP via WhatsApp.
            Powered by ZimHub.
          </p>
        </div>
      </section>

      {top.top_promoters?.length > 0 && (
        <section>
          <h2 className="font-display text-lg text-ink mb-3 heading-accent">Top promoters</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {top.top_promoters.slice(0, 3).map((p) => (
              <div key={p.promoter_id} className="card p-3 flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-bgs2 overflow-hidden shrink-0">
                  {p.photo_url ? <img src={p.photo_url} className="h-full w-full object-cover" /> : null}
                </div>
                <div className="min-w-0">
                  <div className="text-sm text-ink truncate font-medium">
                    {p.organisation_name || p.name}
                  </div>
                  <div className="text-[11px] text-inkm">
                    {p.completed_purchases_30d} sale{p.completed_purchases_30d === 1 ? '' : 's'} / 30d
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
            <input
              className="input-base pl-9"
              placeholder="Search events"
              value={filters.q}
              onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
            />
          </div>
          <select
            className="input-base sm:w-40"
            value={filters.category}
            onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
          >
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select
            className="input-base sm:w-36"
            value={filters.mode}
            onChange={(e) => setFilters((f) => ({ ...f, mode: e.target.value }))}
          >
            <option value="all">All formats</option>
            <option value="ticketed">Ticketed</option>
            <option value="flyer">Flyer</option>
          </select>
          <select
            className="input-base sm:w-36"
            value={filters.timing}
            onChange={(e) => setFilters((f) => ({ ...f, timing: e.target.value }))}
          >
            <option value="upcoming">Upcoming</option>
            <option value="past">Past</option>
            <option value="all">All</option>
          </select>
        </div>

        {loading ? (
          <div className="text-inkm flex items-center gap-2 py-12 justify-center">
            <Loader2 className="animate-spin" size={16} /> Loading events…
          </div>
        ) : events.length === 0 ? (
          <div className="card p-8 text-center text-inkm">
            No events match your filters yet.
          </div>
        ) : (
          <>
            {upcoming.length > 0 && (
              <div className="mb-8">
                <h2 className="font-display text-xl text-ink mb-4 heading-accent">Upcoming</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {upcoming.map((e) => <EventCard key={e.id} event={e} />)}
                </div>
              </div>
            )}
            {past.length > 0 && (
              <div>
                <h2 className="font-display text-lg text-inkm mb-3">Past events</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {past.map((e) => <EventCard key={e.id} event={e} />)}
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
