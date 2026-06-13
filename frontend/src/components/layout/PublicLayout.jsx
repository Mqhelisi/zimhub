import React, { useState, useRef, useEffect } from 'react';
import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { ChevronDown, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { DemoModeBanner } from './DemoModeBanner.jsx';
import { NotificationBell } from '../NotificationBell.jsx';
import { CartIcon } from '../../sections/shop/components/CartIcon.jsx';
import { initials } from '../../utils/time.js';

function BrandMark() {
  return (
    <Link to="/" className="flex items-center gap-2.5 group">
      <span className="relative inline-flex h-9 w-9 items-center justify-center rounded-full bg-brand text-[rgb(20_15_8)] shadow-glow">
        <span className="font-display text-xl font-bold leading-none">Z</span>
      </span>
      <span className="font-display text-2xl text-ink leading-none group-hover:text-brand transition-colors">
        ZimHub
      </span>
    </Link>
  );
}

function UserPill() {
  const { user, adminEntries, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link to="/login" className="btn-ghost">Sign in</Link>
        <Link to="/signup" className="btn-secondary">Sign up</Link>
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-bordr bg-bgs2 py-1 pl-1 pr-3 hover:border-brand/40 transition"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand text-[10.5px] font-bold text-[rgb(20_15_8)]">
          {initials(user.name)}
        </span>
        <span className="hidden sm:inline text-sm text-ink">Welcome, {user.name.split(' ')[0]}</span>
        <ChevronDown size={14} className="text-inkm" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-64 card p-1.5 shadow-2xl">
          <div className="px-3 py-2 text-xs uppercase tracking-wider text-inkm">
            Signed in as<br/><span className="text-ink normal-case tracking-normal">{user.email}</span>
          </div>
          <div className="my-1 h-px bg-bordr" />
          {(adminEntries || []).map((entry, i) => (
            <button
              key={entry.key + i}
              onClick={() => { setOpen(false); navigate(entry.route); }}
              className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm text-ink hover:bg-bgs2"
            >
              <span className="flex items-center gap-2">
                <UserIcon size={14} className="text-inkm" /> {entry.label}
              </span>
              {entry.coming_soon && <span className="pill !py-0.5 !text-[9.5px]">Coming soon</span>}
            </button>
          ))}
          <div className="my-1 h-px bg-bordr" />
          <button
            onClick={async () => { await logout(); setOpen(false); navigate('/'); }}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-danger hover:bg-danger/10"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function PublicLayout() {
  const { user } = useAuth();
  const { pathname } = useLocation();

  // Routes that wrap themselves (Shop section, purchase pages) handle their
  // own top spacing. Don't double-pad them.
  const selfPaddingRoutes = ['/shop', '/purchases', '/my/purchases'];
  const selfPads = selfPaddingRoutes.some((p) => pathname === p || pathname.startsWith(p + '/'));
  const mainCls = selfPads ? '' : 'container-page py-10 sm:py-14';

  return (
    <div className="min-h-screen">
      <DemoModeBanner />
      <header className="sticky top-0 z-20 border-b border-bordr bg-bgp/85 backdrop-blur">
        <div className="container-page flex h-16 items-center justify-between">
          <BrandMark />
          <div className="flex items-center gap-2 sm:gap-3">
            <Link to="/sell" className="hidden sm:inline btn-ghost">Sell on ZimHub</Link>
            <Link to="/shop" className="hidden sm:inline btn-ghost">Shop</Link>
            <CartIcon />
            {user && <NotificationBell />}
            <UserPill />
          </div>
        </div>
      </header>
      <main className={mainCls}>
        <Outlet />
      </main>
      <footer className="mt-16 border-t border-bordr py-10 text-center text-xs text-inkm">
        <div className="container-page">
          <p>ZimHub — Bulawayo's marketplace, in one place. © {new Date().getFullYear()}</p>
          <p className="mt-1 opacity-70">V1 — Shop · Events · Services · Creators</p>
        </div>
      </footer>
    </div>
  );
}
