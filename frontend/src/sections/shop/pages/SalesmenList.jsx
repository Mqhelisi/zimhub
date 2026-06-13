import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { useDebounce } from '../../../hooks/useDebounce.js';
import { shopApi } from '../api.js';
import { SalesmanCard } from '../components/SalesmanCard.jsx';

export default function SalesmenList() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');
  const dq = useDebounce(q, 250);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const next = new URLSearchParams();
    if (dq) next.set('q', dq);
    setParams(next, { replace: true });
  }, [dq, setParams]);

  useEffect(() => {
    let alive = true;
    setData(null); setError('');
    shopApi.listSalesmen({ q: dq || undefined })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load shops.'));
    return () => { alive = false; };
  }, [dq]);

  return (
    <div className="container-page py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-3xl text-ink heading-accent">Shops</h1>
        <Link to="/shop" className="text-sm text-brand hover:underline">← Shop home</Link>
      </div>
      <div className="relative mt-5 max-w-md">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
        <Input
          placeholder="Search by shop name or owner…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="!pl-9"
        />
      </div>
      {error && <div className="mt-6 text-danger">{error}</div>}
      {!data && !error && <div className="mt-10 flex justify-center"><Spinner size={22} /></div>}
      {data && data.salesmen?.length === 0 && (
        <Card className="mt-6 text-center text-inkm">No shops match that search.</Card>
      )}
      {data && data.salesmen?.length > 0 && (
        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.salesmen.map((s) => <SalesmanCard key={s.user_id} salesman={s} />)}
        </div>
      )}
    </div>
  );
}
