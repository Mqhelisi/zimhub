import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MapPin, Phone, Store, ShoppingBag } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { shopApi } from '../api.js';
import { ProductCard } from '../components/ProductCard.jsx';
import { NdebeleDivider } from '../components/NdebeleDivider.jsx';

export default function SalesmanProfile() {
  const { slug } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setData(null); setError('');
    shopApi.salesmanDetail(slug)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load this shop.'));
    return () => { alive = false; };
  }, [slug]);

  if (error) return <div className="container-page py-10 text-danger">{error}</div>;
  if (!data) return <div className="container-page py-16 flex justify-center"><Spinner size={24} /></div>;

  const { salesman, products } = data;
  return (
    <div>
      <div className="relative">
        {salesman.banner_url ? (
          <div
            className="h-48 lg:h-60 w-full bg-cover bg-center"
            style={{ backgroundImage: `url(${salesman.banner_url})` }}
            aria-hidden="true"
          />
        ) : (
          <div className="h-32 w-full shop-hero" aria-hidden="true" />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/40 to-transparent" />

        <div className="container-page relative -mt-14 lg:-mt-16">
          <div className="flex items-end gap-4">
            {salesman.photo_url ? (
              <img
                src={salesman.photo_url} alt=""
                className="h-24 w-24 lg:h-28 lg:w-28 rounded-full object-cover ring-4 ring-bg shadow-soft"
              />
            ) : (
              <div className="h-24 w-24 lg:h-28 lg:w-28 rounded-full bg-bgs2 ring-4 ring-bg flex items-center justify-center text-brand">
                <Store size={32} />
              </div>
            )}
            <div className="pb-2 min-w-0">
              <h1 className="font-display text-3xl lg:text-4xl text-ink truncate">
                {salesman.shop_name}
              </h1>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-inkm">
                {salesman.suburb && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin size={12} /> {salesman.suburb}
                  </span>
                )}
                {salesman.phone && (
                  <span className="inline-flex items-center gap-1">
                    <Phone size={12} /> {salesman.phone}
                  </span>
                )}
                <span>{salesman.product_count} product{salesman.product_count !== 1 ? 's' : ''}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container-page mt-6 grid gap-6 lg:grid-cols-3">
        <aside className="lg:col-span-1 space-y-3">
          {salesman.bio && (
            <Card>
              <h3 className="font-display text-lg text-ink">About</h3>
              <p className="mt-2 text-sm text-inkm whitespace-pre-wrap">{salesman.bio}</p>
            </Card>
          )}
          {salesman.pickup_delivery_policy && (
            <Card>
              <h3 className="font-display text-lg text-ink">Pickup & delivery</h3>
              <p className="mt-2 text-sm text-inkm whitespace-pre-wrap">
                {salesman.pickup_delivery_policy}
              </p>
            </Card>
          )}
        </aside>

        <div className="lg:col-span-2">
          <h2 className="font-display text-2xl text-ink heading-accent inline-flex items-center gap-2">
            <ShoppingBag size={18} className="text-brand" /> All products
          </h2>
          <NdebeleDivider className="sm mt-3" />
          {products?.length ? (
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
              {products.map((p) => (
                <ProductCard key={p.id} product={p} compact />
              ))}
            </div>
          ) : (
            <p className="mt-4 text-inkm">No products listed yet.</p>
          )}
        </div>
      </div>
      <div className="h-16" />
    </div>
  );
}
