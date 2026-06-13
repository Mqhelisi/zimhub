import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Music2, Images, CalendarDays, PlayCircle, ArrowRight } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl border border-bordr bg-bgs p-4">
      <div className="flex items-center gap-2 text-inkm"><Icon size={15} /> <span className="text-xs">{label}</span></div>
      <div className="mt-1 font-display text-3xl text-ink">{value}</div>
    </div>
  );
}

export default function CreatorDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    creatorApi.dashboard().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);
  if (loading) return <div className="flex items-center gap-2 py-16 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>;
  if (!data) return <p className="text-inkm">Could not load your studio.</p>;
  const c = data.counts;
  return (
    <div>
      <h1 className="accent-rule font-display text-4xl text-ink">Welcome back, {data.profile.display_name}</h1>
      <p className="mt-2 text-sm text-inkm">Your public page lives at <Link to={`/creators/${data.profile.creator_slug}`} className="text-ink underline">/creators/{data.profile.creator_slug}</Link></p>

      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat icon={Music2} label="Tracks" value={c.tracks} />
        <Stat icon={PlayCircle} label="Total plays" value={c.total_plays} />
        <Stat icon={Images} label="Gallery items" value={c.gallery_items} />
        <Stat icon={CalendarDays} label="Upcoming events" value={c.upcoming_events} />
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-2">
        <Link to="/creator/music" className="flex items-center justify-between rounded-xl border border-bordr bg-bgs p-4 hover:border-[rgb(var(--section-accent)/0.6)]">
          <span className="flex items-center gap-2 text-ink"><Music2 size={16} /> Manage music</span><ArrowRight size={16} className="text-inkm" />
        </Link>
        <Link to="/creator/gallery" className="flex items-center justify-between rounded-xl border border-bordr bg-bgs p-4 hover:border-[rgb(var(--section-accent)/0.6)]">
          <span className="flex items-center gap-2 text-ink"><Images size={16} /> Manage gallery</span><ArrowRight size={16} className="text-inkm" />
        </Link>
        <Link to="/creator/events" className="flex items-center justify-between rounded-xl border border-bordr bg-bgs p-4 hover:border-[rgb(var(--section-accent)/0.6)]">
          <span className="flex items-center gap-2 text-ink"><CalendarDays size={16} /> Manage events</span><ArrowRight size={16} className="text-inkm" />
        </Link>
        <Link to="/creator/profile" className="flex items-center justify-between rounded-xl border border-bordr bg-bgs p-4 hover:border-[rgb(var(--section-accent)/0.6)]">
          <span className="flex items-center gap-2 text-ink">Edit profile & page</span><ArrowRight size={16} className="text-inkm" />
        </Link>
      </div>

      {data.upcoming_events?.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 font-display text-2xl text-ink">Upcoming events</h2>
          <div className="space-y-2">
            {data.upcoming_events.map((e) => (
              <div key={e.id} className="flex items-center justify-between rounded-lg border border-bordr bg-bgs px-4 py-3">
                <div>
                  <div className="text-sm font-medium text-ink">{e.title}</div>
                  <div className="text-xs text-inkm">{new Date(e.event_date).toLocaleDateString('en-ZW', { timeZone: 'Africa/Harare' })} · {e.ticketing_mode === 'host_ticketing' ? 'Ticketed' : 'Free / external'}</div>
                </div>
                <Link to="/creator/events" className="text-xs text-inkm hover:text-ink">Manage →</Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
