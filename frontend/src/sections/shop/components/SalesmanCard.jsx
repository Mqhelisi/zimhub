import React from 'react';
import { Link } from 'react-router-dom';
import { Store, MapPin } from 'lucide-react';

export function SalesmanCard({ salesman }) {
  return (
    <Link
      to={`/shop/salesman/${salesman.shop_slug}`}
      className="card flex items-center gap-3 !p-3 hover:border-brand/60 transition"
    >
      {salesman.photo_url ? (
        <img
          src={salesman.photo_url}
          alt=""
          className="h-12 w-12 shrink-0 rounded-full object-cover ring-1 ring-bordr"
          loading="lazy"
        />
      ) : (
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-bgs2 text-inkm">
          <Store size={20} />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium text-ink">{salesman.shop_name}</div>
        <div className="flex items-center gap-2 text-xs text-inkm truncate">
          {salesman.suburb && (
            <span className="inline-flex items-center gap-0.5">
              <MapPin size={11} /> {salesman.suburb}
            </span>
          )}
          <span>{salesman.product_count} product{salesman.product_count !== 1 ? 's' : ''}</span>
        </div>
      </div>
    </Link>
  );
}
