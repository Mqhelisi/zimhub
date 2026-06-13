import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Badge } from '../../components/ui/Badge.jsx';
import { superUsersApi } from '../../api/superUsers.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import { formatDateTime, initials } from '../../utils/time.js';

const CAPABILITIES = [
  { key: '', label: 'All capabilities' },
  { key: 'is_buyer', label: 'Buyers' },
  { key: 'is_salesman', label: 'Salesmen' },
  { key: 'is_promoter', label: 'Promoters' },
  { key: 'is_provider', label: 'Providers' },
  { key: 'is_creator', label: 'Creators' },
  { key: 'is_super_admin', label: 'Super admins' },
];

const STATUSES = [
  { key: '', label: 'All statuses' },
  { key: 'active', label: 'Active' },
  { key: 'suspended', label: 'Suspended' },
];

export default function UsersList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const capability = searchParams.get('capability') || '';
  const status = searchParams.get('status') || '';
  const [q, setQ] = useState(searchParams.get('q') || '');
  const debouncedQ = useDebounce(q, 300);
  const page = parseInt(searchParams.get('page') || '1', 10);

  const [data, setData] = useState({ users: [], total: 0, page: 1, page_size: 20 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    superUsersApi.list({ capability, status, q: debouncedQ, page })
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(e?.response?.data?.message || 'Could not load users.'))
      .finally(() => setLoading(false));
  }, [capability, status, debouncedQ, page]);

  const update = (k, v) => {
    const next = new URLSearchParams(searchParams);
    if (v) next.set(k, v); else next.delete(k);
    if (k !== 'page') next.delete('page');
    setSearchParams(next);
  };

  useEffect(() => { update('q', debouncedQ); /* eslint-disable-next-line */ }, [debouncedQ]);

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">Users</h1>
      <p className="mt-1 text-sm text-inkm">All ZimHub accounts — search, filter, and manage capabilities.</p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select value={capability} onChange={(e) => update('capability', e.target.value)} className="input-base max-w-[12rem]">
          {CAPABILITIES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
        <select value={status} onChange={(e) => update('status', e.target.value)} className="input-base max-w-[10rem]">
          {STATUSES.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
        <div className="relative max-w-md flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, email, phone…"
            className="input-base pl-9"
          />
        </div>
      </div>

      {error && <div className="mt-4 text-danger">{error}</div>}

      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-10"><Spinner /></div>
        ) : data.users.length === 0 ? (
          <Card className="text-center text-inkm">No users match these filters.</Card>
        ) : (
          <div className="card divide-y divide-bordr !p-0">
            {data.users.map((u) => (
              <button
                key={u.id}
                onClick={() => navigate(`/super/users/${u.id}`)}
                className="flex w-full items-center gap-4 px-4 py-3 text-left transition hover:bg-bgs2"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-bgs2 text-sm font-semibold text-ink">
                  {initials(u.name)}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-ink">{u.name}</span>
                    {u.status === 'suspended' && <Badge tone="danger">Suspended</Badge>}
                    {(u.capability_pills || []).map((c) => (
                      <Badge key={c} category={c}>{c.replace('is_', '')}</Badge>
                    ))}
                  </div>
                  <div className="mt-0.5 truncate text-xs text-inkm">
                    {u.email} · {u.phone}{u.suburb ? ` · ${u.suburb}` : ''}
                  </div>
                </div>
                <div className="shrink-0 text-[10px] uppercase tracking-wider text-inkm/70">
                  Joined {formatDateTime(u.created_at)}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-xs text-inkm">
          <span>Page {data.page} of {totalPages} · {data.total} users</span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              onClick={() => update('page', String(data.page - 1))}
              className="btn-secondary !py-1.5 disabled:opacity-40"
            >
              ← Prev
            </button>
            <button
              disabled={data.page >= totalPages}
              onClick={() => update('page', String(data.page + 1))}
              className="btn-secondary !py-1.5 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
