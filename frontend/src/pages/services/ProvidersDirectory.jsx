// /services/providers — directory with trade chips, suburb filter (Services-
// only per master spec §16.13), search, pagination.
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { listProviders } from '../../components/services/api.js';
import { ProviderCard } from '../../components/services/ServicesSectionLayout.jsx';
import { useDebounce } from '../../hooks/useDebounce.js';

export default function ProvidersDirectory() {
  const [params, setParams] = useSearchParams();
  const trade = params.get('trade') || '';
  const suburb = params.get('suburb') || '';
  const page = parseInt(params.get('page') || '1', 10);
  const [q, setQ] = useState(params.get('q') || '');
  const debouncedQ = useDebounce(q, 350);
  const [data, setData] = useState(null);

  useEffect(() => {
    listProviders({ trade, suburb, q: debouncedQ, page })
      .then(setData)
      .catch(() => setData({ providers: [], total: 0, facets: { trades: [], suburbs: [] } }));
  }, [trade, suburb, debouncedQ, page]);

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    next.delete('page');
    setParams(next, { replace: true });
  };

  const pages = data ? Math.max(1, Math.ceil(data.total / (data.page_size || 12))) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">Find a provider</h1>
        <p className="mt-1 text-sm text-inkm">
          Filter by trade or suburb, or search by name and service.
        </p>
      </div>

      <div className="card space-y-4 p-4">
        <input
          className="input"
          placeholder="Search providers or services…"
          value={q}
          onChange={(e) => { setQ(e.target.value); }}
          aria-label="Search"
        />
        <div className="flex flex-wrap gap-2">
          {(data?.facets?.trades || []).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setParam('trade', trade === t ? '' : t)}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                trade === t
                  ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.15)] text-ink'
                  : 'border-bordr bg-bgs text-inkm hover:text-ink'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        {(data?.facets?.suburbs || []).length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs uppercase tracking-wider text-inkm">Suburb</span>
            {data.facets.suburbs.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setParam('suburb', suburb === s ? '' : s)}
                className={`rounded-full border px-3 py-1 text-xs transition ${
                  suburb === s
                    ? 'border-[rgb(var(--section-highlight))] bg-[rgb(var(--section-highlight)/0.12)] text-[rgb(var(--section-highlight))]'
                    : 'border-bordr bg-bgs text-inkm hover:text-ink'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {data === null && <p className="text-sm text-inkm">Loading…</p>}
      {data && data.providers.length === 0 && (
        <div className="card p-8 text-center text-inkm">
          No providers match those filters yet — try clearing one.
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(data?.providers || []).map((p) => <ProviderCard key={p.user_id} provider={p} />)}
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <button
            className="btn-secondary"
            disabled={page <= 1}
            onClick={() => setParam('page', String(page - 1))}
          >
            ← Previous
          </button>
          <span className="text-inkm">Page {page} of {pages}</span>
          <button
            className="btn-secondary"
            disabled={page >= pages}
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set('page', String(page + 1));
              setParams(next, { replace: true });
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
