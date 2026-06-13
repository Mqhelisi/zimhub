import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { ShoppingBag, ShoppingCart, ChevronLeft } from 'lucide-react';
import { useAllCarts } from '../hooks/useCart.js';
import { NdebeleDivider } from './NdebeleDivider.jsx';
import '../theme/theme-shop.css';

export default function ShopSectionLayout() {
  const { totalUnits } = useAllCarts();
  const { pathname } = useLocation();
  const showBackToHub = pathname.startsWith('/shop/') || pathname.startsWith('/cart');

  return (
    <div data-section="shop">
      <div className="bg-bgs2/60 border-b border-bordr/60">
        <div className="container-page py-2 flex items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-3 min-w-0">
            {showBackToHub && (
              <Link to="/" className="text-inkm hover:text-ink inline-flex items-center gap-1">
                <ChevronLeft size={14} /> Hub
              </Link>
            )}
            <Link to="/shop" className="text-ink inline-flex items-center gap-2 font-medium min-w-0">
              <ShoppingBag size={16} className="text-brand shrink-0" />
              <span className="truncate">ZimHub Shop</span>
            </Link>
          </div>
          <Link
            to="/shop/cart"
            className="relative inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-inkm hover:text-ink hover:bg-bgs2"
          >
            <ShoppingCart size={16} />
            <span>Cart</span>
            {totalUnits > 0 && (
              <span className="ml-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-brand px-1.5 text-[11px] font-semibold text-bg">
                {totalUnits}
              </span>
            )}
          </Link>
        </div>
        <NdebeleDivider className="sm" />
      </div>

      <Outlet />
    </div>
  );
}
