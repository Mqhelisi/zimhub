import React from 'react';
import { Outlet, NavLink, Link, Navigate } from 'react-router-dom';
import {
  LayoutDashboard, Package, CreditCard, User, ExternalLink, ShoppingBag, LogOut,
} from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext.jsx';
import { NotificationBell } from '../../../components/NotificationBell.jsx';
import '../../shop/theme/theme-shop.css';

const NAV = [
  { to: '/salesman', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/salesman/products', icon: Package, label: 'Products' },
  { to: '/salesman/pending-payments', icon: CreditCard, label: 'Pending payments' },
  { to: '/salesman/profile', icon: User, label: 'Shop profile' },
];

export default function SalesmanLayout() {
  const { user, logout } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_salesman) return <Navigate to="/" replace />;
  if (user.password_reset_required) return <Navigate to="/change-password" replace />;

  const shopSlug = user.salesman_profile?.shop_slug;

  return (
    <div data-section="shop" className="min-h-screen flex flex-col lg:flex-row">
      <aside className="lg:w-64 lg:shrink-0 lg:border-r lg:border-bordr lg:bg-bgs2/30 lg:min-h-screen">
        <div className="border-b border-bordr p-4 flex items-center justify-between">
          <Link to="/salesman" className="inline-flex items-center gap-2 font-display text-lg text-ink">
            <ShoppingBag size={18} className="text-brand" /> Salesman
          </Link>
          <NotificationBell />
        </div>
        <nav className="p-2 lg:p-3 space-y-0.5">
          {NAV.map((n) => (
            <NavLink
              key={n.to} to={n.to} end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition
                 ${isActive
                    ? 'bg-brand/15 text-brand'
                    : 'text-inkm hover:bg-bgs2 hover:text-ink'}`
              }
            >
              <n.icon size={16} /> {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-bordr p-3 space-y-2">
          {shopSlug && (
            <Link
              to={`/shop/salesman/${shopSlug}`}
              className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-inkm hover:bg-bgs2 hover:text-ink"
            >
              <ExternalLink size={14} /> View public shop
            </Link>
          )}
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-inkm hover:bg-bgs2 hover:text-ink"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <div className="container-page py-6 lg:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
