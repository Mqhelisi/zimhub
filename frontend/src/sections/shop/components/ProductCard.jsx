import React from 'react';
import { Link } from 'react-router-dom';
import { ShoppingBag } from 'lucide-react';

export function ProductCard({ product, compact = false }) {
  const photo = (product.photos || [])[0];
  const available = Number(product.available ?? product.stock_quantity ?? 0);
  const lowStock = available > 0 && available <= 3;
  const soldOut = available === 0;

  return (
    <Link
      to={`/shop/product/${product.id}`}
      className="group card overflow-hidden !p-0 hover:border-brand/60 transition flex flex-col"
    >
      <div className="relative aspect-[4/3] w-full bg-bgs2 overflow-hidden">
        {photo ? (
          <img
            src={photo}
            alt={product.name}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-inkm">
            <ShoppingBag size={28} />
          </div>
        )}
        {soldOut && (
          <div className="absolute inset-x-0 bottom-0 bg-bgp/90 px-2 py-1 text-center text-xs font-medium text-danger backdrop-blur-sm">
            Sold out
          </div>
        )}
        {!soldOut && lowStock && (
          <div className="absolute top-2 right-2 rounded-full bg-warning/95 px-2 py-0.5 text-[10px] font-semibold text-bg">
            Only {available} left
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <div className="line-clamp-2 text-sm text-ink min-h-[2.5em]">{product.name}</div>
        {!compact && product.salesman && (
          <div className="text-xs text-inkm truncate">{product.salesman.shop_name}</div>
        )}
        <div className="mt-auto pt-1 font-display text-lg text-brand">
          ${Number(product.price_usd).toFixed(2)}
        </div>
      </div>
    </Link>
  );
}
