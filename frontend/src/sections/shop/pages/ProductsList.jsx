import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { Select } from '../../../components/ui/Select.jsx';
import { useDebounce } from '../../../hooks/useDebounce.js';
import { shopApi } from '../api.js';
import { ProductCard } from '../components/ProductCard.jsx';

export default function ProductsList() {
  const [params, setParams] = useSearchParams();
  const initialQ = params.get('q') || '';
  const initialCat = params.get('category') || '';

  const [q, setQ] = useState(initialQ);
  const [category, setCategory] = useState(initialCat);
  const dq = useDebounce(q, 250);

  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    shopApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    // Sync URL params
    const next = new URLSearchParams();
    if (dq) next.set('q', dq);
    if (category) next.set('category', category);
    setParams(next, { replace: true });
  }, [dq, category, setParams]);

  useEffect(() => {
    let alive = true;
    setData(null); setError('');
    shopApi.listProducts({ q: dq || undefined, category: category || undefined })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load products.'));
    return () => { alive = false; };
  }, [dq, category]);

  return (
    <div className="container-page py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-3xl text-ink heading-accent">Products</h1>
        <Link to="/shop" className="text-sm text-brand hover:underline">← Shop home</Link>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-[1fr,200px,auto]">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-inkm" />
          <Input
            placeholder="Search products or shops…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="!pl-9"
          />
        </div>
        <Select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </Select>
        {(q || category) && (
          <button
            onClick={() => { setQ(''); setCategory(''); }}
            className="rounded-md border border-bordr bg-bgs2/50 px-3 py-2 text-sm text-inkm hover:text-ink inline-flex items-center justify-center gap-1"
          >
            <X size={14} /> Clear
          </button>
        )}
      </div>

      {error && <div className="mt-6 text-danger">{error}</div>}
      {!data && !error && <div className="mt-10 flex justify-center"><Spinner size={22} /></div>}
      {data && data.products?.length === 0 && (
        <Card className="mt-6 text-center text-inkm">
          No products match those filters.
        </Card>
      )}
      {data && data.products?.length > 0 && (
        <>
          <p className="mt-4 text-xs text-inkm">{data.total} product{data.total !== 1 ? 's' : ''}</p>
          <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {data.products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
