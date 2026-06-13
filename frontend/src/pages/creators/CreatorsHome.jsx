import React, { useEffect, useState } from 'react';
import { Loader2, Music2 } from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { CreatorCard, TrackList } from '../../modules/creator_platform/components/index.jsx';
import { useToast } from '../../components/ui/Toast.jsx';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'musician', label: 'Musicians' },
  { key: 'photographer', label: 'Photographers' },
  { key: 'visual_artist', label: 'Visual Artists' },
];

export default function CreatorsHome() {
  const toast = useToast();
  const [creators, setCreators] = useState([]);
  const [topTracks, setTopTracks] = useState([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    creatorApi.listCreators({ type: filter || undefined })
      .then((r) => setCreators(r.creators))
      .catch((e) => toast.error(e.message || 'Could not load creators'))
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => {
    creatorApi.landing().then((r) => setTopTracks(r.top_tracks || [])).catch(() => {});
  }, []);

  return (
    <main className="container-page py-10">
      {/* Editorial hero */}
      <header className="max-w-2xl">
        <p className="text-xs uppercase tracking-[0.2em] text-inkm">Bulawayo · on the record</p>
        <h1 className="accent-rule mt-2 font-display text-5xl leading-[1.05] text-ink sm:text-6xl">
          The city's creators,<br />in their own light.
        </h1>
        <p className="mt-5 text-base text-inkm">
          Stream local music, walk through photo and art collections, and catch
          the next show — from Bulawayo musicians, photographers, and visual artists.
          No account needed to listen.
        </p>
      </header>

      {/* Type filter */}
      <div className="mt-8 flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = filter === f.key;
          return (
            <button
              key={f.key || 'all'}
              onClick={() => setFilter(f.key)}
              className={`rounded-full border px-4 py-1.5 text-sm transition ${
                active
                  ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.14)] text-[rgb(var(--section-accent))]'
                  : 'border-bordr text-inkm hover:text-ink'
              }`}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Creator grid */}
      <section className="mt-6">
        {loading ? (
          <div className="flex items-center gap-2 py-16 text-inkm">
            <Loader2 className="animate-spin" size={16} /> Loading creators…
          </div>
        ) : creators.length === 0 ? (
          <p className="py-16 text-inkm">No creators in this category yet.</p>
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {creators.map((c) => (
              <CreatorCard key={c.user_id} creator={c} />
            ))}
          </div>
        )}
      </section>

      {/* Top tracks strip */}
      {topTracks.length > 0 && (
        <section className="mt-14">
          <h2 className="mb-4 flex items-center gap-2 font-display text-2xl text-ink">
            <Music2 size={18} style={{ color: 'rgb(var(--section-accent))' }} /> Top tracks this week
          </h2>
          <TrackList tracks={topTracks} />
        </section>
      )}
    </main>
  );
}
