import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Plus, Search, Pencil, Archive, ShoppingBag } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { useDebounce } from '../../../hooks/useDebounce.js';
import { shopApi } from '../../shop/api.js';

const STATUS_TABS = [
  { key: '', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'draft', label: 'Draft' },
  { key: 'archived', label: 'Archived' },
];

const STATUS_TONE = {
  active: 'text-success',
  draft: 'text-warning',
  archived: 'text-inkm',
};

export default function Products() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');
  const [status, setStatus] = useState(params.get('status') || '');
  const dq = useDebounce(q, 250);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const next = new URLSearchParams();
    if (dq) next.set('q', dq);
    if (status) next.set('status', status);
    setParams(next, { replace: true });
  }, [dq, status, setParams]);

  useEffect(() => {
    let alive = true;
    setData(null); setError('');
    shopApi.admin.listProducts({ q: dq || undefined, status: status || undefined })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load products.'));
    return () => { alive = false; };
  }, [dq, status]);

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-ink">Products</h1>
          <p className="mt-1 text-sm text-inkm">Your catalog.</p>
        </div>
        <Link to="/salesman/products/new">
          <Button variant="primary"><Plus size={14} /> New product</Button>
        </Link>
      </div>

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <div className="relative max-w-sm flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
          <Input
            placeholder="Search by name or description"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="!pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {STATUS_TABS.map((t) => (
            <button
              key={t.key || 'all'} onClick={() => setStatus(t.key)}
              className={`rounded-full px-3 py-1 text-sm transition
                ${status === t.key ? 'bg-brand text-bg' : 'text-inkm hover:bg-bgs2 hover:text-ink'}`}
            >{t.label}</button>
          ))}
        </div>
      </div>

      {error && <div className="mt-6 text-danger">{error}</div>}
      {!data && !error && <div className="mt-10 flex justify-center"><Spinner size={22} /></div>}

      {data && data.products?.length === 0 && (
        <Card className="mt-6 text-center">
          <ShoppingBag size={28} className="mx-auto text-inkm" />
          <p className="mt-2 text-inkm">
            {q || status ? 'No products match your filters.' : 'No products yet — add your first.'}
          </p>
        </Card>
      )}
      {data && data.products?.length > 0 && (
        <ul className="mt-5 space-y-2">
          {data.products.map((p) => (
            <li key={p.id}>
              <Link
                to={`/salesman/products/${p.id}`}
                className="card flex items-center gap-3 !p-3 hover:border-brand/60"
              >
                {p.photos?.[0] ? (
                  <img src={p.photos[0]} alt=""
                       className="h-14 w-14 shrink-0 rounded-md object-cover ring-1 ring-bordr" />
                ) : (
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md bg-bgs2 text-inkm">
                    <ShoppingBag size={18} />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-ink">{p.name}</div>
                  <div className="text-xs text-inkm">
                    {p.category} • {p.available} avail.{' '}
                    {p.stock_held > 0 && <span className="text-warning">• {p.stock_held} held</span>}
                    {' • '}
                    <span className={STATUS_TONE[p.status] || 'text-inkm'}>{p.status}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-display text-lg text-brand">${Number(p.price_usd).toFixed(2)}</div>
                  <div className="mt-0.5 text-xs text-inkm inline-flex items-center gap-0.5">
                    <Pencil size={10} /> edit
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
