import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Badge } from '../../components/ui/Badge.jsx';
import { signupRequestsApi } from '../../api/signupRequests.js';
import { formatRelative, initials } from '../../utils/time.js';
import { useDebounce } from '../../hooks/useDebounce.js';

const STATUSES = [
  { key: '', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
];

const CATEGORIES = [
  { key: '', label: 'All categories' },
  { key: 'salesman', label: 'Salesman' },
  { key: 'promoter', label: 'Promoter' },
  { key: 'provider', label: 'Provider' },
  { key: 'creator', label: 'Creator' },
];

export default function SignupRequestsInbox() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const status = searchParams.get('status') || '';
  const category = searchParams.get('category') || '';
  const [q, setQ] = useState(searchParams.get('q') || '');
  const debouncedQ = useDebounce(q, 300);

  const [data, setData] = useState({ requests: [], counts: { pending: 0, approved: 0, rejected: 0 } });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    signupRequestsApi.list({ status, category, q: debouncedQ })
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(e?.response?.data?.message || 'Could not load applications.'))
      .finally(() => setLoading(false));
  }, [status, category, debouncedQ]);

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next);
  };

  useEffect(() => {
    updateParam('q', debouncedQ);
     
  }, [debouncedQ]);

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">Applications</h1>
      <p className="mt-1 text-sm text-inkm">Review and process incoming seller signup requests.</p>

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-2">
        {STATUSES.map((s) => {
          const active = status === s.key;
          const count = s.key ? data.counts[s.key] : (data.counts.pending + data.counts.approved + data.counts.rejected);
          return (
            <button
              key={s.key || 'all'}
              onClick={() => updateParam('status', s.key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                active ? 'border-brand bg-brand text-[rgb(20_15_8)]' : 'border-bordr bg-bgs text-inkm hover:text-ink'
              }`}
            >
              {s.label}
              <span className="ml-1.5 opacity-80">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <select
          value={category}
          onChange={(e) => updateParam('category', e.target.value)}
          className="input-base max-w-[12rem]"
        >
          {CATEGORIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
        <div className="relative max-w-md flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, business, email…"
            className="input-base pl-9"
          />
        </div>
      </div>

      <div className="mt-6">
        {error && <div className="text-danger">{error}</div>}
        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : data.requests.length === 0 ? (
          <Card className="text-center text-inkm">No applications match these filters.</Card>
        ) : (
          <div className="card divide-y divide-bordr !p-0">
            {data.requests.map((r) => (
              <button
                key={r.id}
                onClick={() => navigate(`/super/signup-requests/${r.id}`)}
                className="flex w-full items-center gap-4 px-4 py-3 text-left transition hover:bg-bgs2"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-bgs2 text-sm font-semibold text-ink">
                  {initials(r.full_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-ink">{r.full_name}</span>
                    <Badge category={r.category}>{r.category}</Badge>
                    {r.status === 'pending' && <Badge tone="warning">Pending</Badge>}
                    {r.status === 'approved' && <Badge tone="success">Approved</Badge>}
                    {r.status === 'rejected' && <Badge tone="danger">Rejected</Badge>}
                  </div>
                  <div className="mt-0.5 truncate text-xs text-inkm">
                    {r.business_name ? `${r.business_name} · ` : ''}{r.suburb} · {r.email}
                  </div>
                </div>
                <div className="shrink-0 text-[10px] uppercase tracking-wider text-inkm/70">
                  {formatRelative(r.created_at)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
