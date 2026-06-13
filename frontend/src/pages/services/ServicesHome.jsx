// /services — Services landing: hero, trade chips, top providers (§6.3).
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Wrench } from 'lucide-react';
import { servicesHome } from '../../components/services/api.js';
import { ProviderCard } from '../../components/services/ServicesSectionLayout.jsx';

const TRADES = ['Plumber', 'Electrician', 'Hairdresser', 'Driver', 'Maid',
  'Mechanic', 'Tutor', 'Photographer-for-hire', 'Other'];

export default function ServicesHome() {
  const [top, setTop] = useState(null);
  const [q, setQ] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    servicesHome().then((d) => setTop(d.top_providers || [])).catch(() => setTop([]));
  }, []);

  return (
    <div className="space-y-10">
      <section className="services-hero -mx-4 rounded-2xl border border-bordr/60 px-6 py-12 sm:px-10 sm:py-16">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-[rgb(var(--section-highlight))]">
          ZimHub · Services
        </p>
        <h1 className="heading-accent mt-2 max-w-2xl font-display text-3xl text-ink sm:text-4xl">
          Book trusted hands across Bulawayo
        </h1>
        <p className="mt-3 max-w-xl text-inkm">
          Plumbers, hairdressers, tutors and more — see real availability, request a time,
          and settle payment directly with your provider.
        </p>
        <form
          className="mt-6 flex max-w-lg gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            navigate(`/services/providers${q ? `?q=${encodeURIComponent(q)}` : ''}`);
          }}
        >
          <input
            className="input"
            placeholder="Search providers or services…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search providers"
          />
          <button type="submit" className="btn-primary shrink-0">
            <Search size={16} /> Search
          </button>
        </form>
      </section>

      <section>
        <h2 className="mb-3 font-display text-lg text-ink">Browse by trade</h2>
        <div className="flex flex-wrap gap-2">
          {TRADES.map((t) => (
            <Link
              key={t}
              to={`/services/providers?trade=${encodeURIComponent(t)}`}
              className="rounded-full border border-bordr bg-bgs px-3.5 py-1.5 text-sm text-inkm transition hover:border-[rgb(var(--section-accent))] hover:text-ink"
            >
              {t}
            </Link>
          ))}
        </div>
      </section>

      <div className="services-divider" aria-hidden="true" />

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg text-ink">Top providers</h2>
          <Link to="/services/providers" className="btn-ghost">Browse all →</Link>
        </div>
        {top === null && <p className="text-sm text-inkm">Loading…</p>}
        {top?.length === 0 && (
          <div className="card p-8 text-center text-inkm">
            <Wrench className="mx-auto mb-2 text-[rgb(var(--section-accent))]" />
            No providers listed yet — check back soon.
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(top || []).map((p) => <ProviderCard key={p.user_id} provider={p} />)}
        </div>
      </section>
    </div>
  );
}
