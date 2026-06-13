import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Store, Tag, ArrowRight } from 'lucide-react';
import { Spinner } from '../../../components/ui/Card.jsx';
import { shopApi } from '../api.js';
import { ProductCard } from '../components/ProductCard.jsx';
import { SalesmanCard } from '../components/SalesmanCard.jsx';
import { NdebeleDivider } from '../components/NdebeleDivider.jsx';

export default function ShopHome() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    shopApi.home()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load Shop.'));
    return () => { alive = false; };
  }, []);

  if (error) return <div className="container-page py-10 text-danger">{error}</div>;
  if (!data) return <div className="container-page py-16 flex justify-center"><Spinner size={24} /></div>;

  return (
    <div>
      {/* Hero */}
      <section className="shop-hero">
        <div className="container-page py-10 lg:py-14">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-widest text-brand">ZimHub Shop</p>
            <h1 className="mt-2 font-display text-4xl lg:text-5xl text-ink leading-tight">
              Buy from real Bulawayo shops.
              <span className="block text-inkm font-normal text-2xl lg:text-3xl">
                Settle on WhatsApp. ZimHub holds the trust.
              </span>
            </h1>
            <div className="mt-6 flex flex-wrap gap-2">
              <Link
                to="/shop/products"
                className="inline-flex items-center gap-1.5 rounded-md bg-brand px-4 py-2 text-sm font-medium text-bg hover:bg-brand-hover"
              >
                Browse all products <ArrowRight size={14} />
              </Link>
              <Link
                to="/shop/salesmen"
                className="inline-flex items-center gap-1.5 rounded-md border border-bordr bg-bgs2/50 px-4 py-2 text-sm text-ink hover:bg-bgs2"
              >
                <Store size={14} /> Find a shop
              </Link>
            </div>
          </div>
        </div>
        <NdebeleDivider />
      </section>

      {/* Categories */}
      <section className="container-page mt-10">
        <h2 className="font-display text-2xl text-ink heading-accent">Categories</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {(data.categories || []).map((c) => (
            <Link
              key={c}
              to={`/shop/products?category=${encodeURIComponent(c)}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-bordr bg-bgs2/40 px-3 py-1.5 text-sm text-ink hover:border-brand/60 hover:text-brand transition"
            >
              <Tag size={12} /> {c}
            </Link>
          ))}
        </div>
      </section>

      {/* Top products */}
      <section className="container-page mt-12">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-2xl text-ink heading-accent inline-flex items-center gap-2">
            <Sparkles size={18} className="text-brand" /> Top products
          </h2>
          <Link to="/shop/products" className="text-sm text-brand hover:underline">See all →</Link>
        </div>
        {data.top_products?.length ? (
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {data.top_products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        ) : (
          <p className="mt-3 text-inkm">No products yet. Be the first Salesman to list.</p>
        )}
      </section>

      {/* Top salesmen */}
      <section className="container-page mt-12 mb-16">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-2xl text-ink heading-accent inline-flex items-center gap-2">
            <Store size={18} className="text-brand" /> Top shops
          </h2>
          <Link to="/shop/salesmen" className="text-sm text-brand hover:underline">See all →</Link>
        </div>
        {data.top_salesmen?.length ? (
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {data.top_salesmen.map((s) => (
              <SalesmanCard key={s.user_id} salesman={s} />
            ))}
          </div>
        ) : (
          <p className="mt-3 text-inkm">No shops yet.</p>
        )}
      </section>
    </div>
  );
}
