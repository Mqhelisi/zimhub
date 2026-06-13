import React from 'react';
import { Link } from 'react-router-dom';
import { ShoppingCart } from 'lucide-react';
import { useAllCarts } from '../hooks/useCart.js';

export function CartIcon({ className = '' }) {
  const { totalUnits } = useAllCarts();
  return (
    <Link
      to="/shop/cart"
      className={`relative inline-flex items-center rounded-md p-2 text-inkm hover:text-ink hover:bg-bgs2 ${className}`}
      aria-label={`Cart (${totalUnits} items)`}
    >
      <ShoppingCart size={18} />
      {totalUnits > 0 && (
        <span className="absolute -top-0.5 -right-0.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-shop px-1 text-[10px] font-semibold text-bg">
          {totalUnits}
        </span>
      )}
    </Link>
  );
}
