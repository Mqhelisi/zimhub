import React from 'react';
import { NavLink, Outlet, Link } from 'react-router-dom';
import { LayoutDashboard, Inbox, Users, Settings, MessageSquare, ArrowLeft, AlertTriangle, CalendarClock } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { DemoModeBanner } from './DemoModeBanner.jsx';
import { NotificationBell } from '../NotificationBell.jsx';
import { initials } from '../../utils/time.js';

const nav = [
  { to: '/super', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/super/signup-requests', label: 'Applications', icon: Inbox },
  { to: '/super/users', label: 'Users', icon: Users },
  { to: '/super/disputes', label: 'Disputes', icon: AlertTriangle },
  { to: '/super/booking-disputes', label: 'Booking disputes', icon: CalendarClock },
  { to: '/super/mock-messages', label: 'Mock messages', icon: MessageSquare },
  { to: '/super/config', label: 'System config', icon: Settings },
];

export function SuperAdminLayout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <DemoModeBanner />
      <div className="flex min-h-[calc(100vh-32px)]">
        <aside className="hidden md:flex sticky top-0 h-screen w-60 shrink-0 flex-col border-r border-bordr bg-bgs/60">
          <Link to="/" className="flex items-center gap-2.5 border-b border-bordr px-5 py-4">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-brand text-[rgb(20_15_8)]">
              <span className="font-display text-base font-bold leading-none">Z</span>
            </span>
            <div>
              <div className="font-display text-base leading-none text-ink">ZimHub</div>
              <div className="text-[10.5px] uppercase tracking-wider text-inkm">Super Admin</div>
            </div>
          </Link>
          <nav className="flex-1 px-2 py-3">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                    isActive
                      ? 'bg-brand/10 text-brand'
                      : 'text-inkm hover:bg-bgs2 hover:text-ink'
                  }`
                }
              >
                <item.icon size={16} />
                {item.label}
              </NavLink>
            ))}
            <div className="my-3 h-px bg-bordr" />
            <Link to="/" className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-inkm hover:bg-bgs2 hover:text-ink transition">
              <ArrowLeft size={16} /> Back to site
            </Link>
          </nav>
          <div className="border-t border-bordr px-3 py-3">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-[11px] font-bold text-[rgb(20_15_8)]">
                {initials(user?.name)}
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium text-ink">{user?.name}</div>
                <div className="truncate text-[10.5px] text-inkm">{user?.email}</div>
              </div>
            </div>
            <button
              onClick={async () => { await logout(); window.location.assign('/'); }}
              className="mt-2 w-full rounded-md border border-bordr px-2 py-1.5 text-xs text-inkm hover:text-danger hover:border-danger/40 transition"
            >
              Sign out
            </button>
          </div>
        </aside>
        <div className="flex-1 min-w-0">
          {/* Mobile top bar */}
          <header className="md:hidden sticky top-0 z-10 flex h-14 items-center justify-between border-b border-bordr bg-bgp/85 backdrop-blur px-4">
            <Link to="/super" className="flex items-center gap-2">
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-brand text-[rgb(20_15_8)]">
                <span className="font-display text-sm font-bold leading-none">Z</span>
              </span>
              <span className="font-display text-base text-ink">Super Admin</span>
            </Link>
            <NotificationBell />
          </header>
          {/* Desktop top bar */}
          <header className="hidden md:flex sticky top-0 z-10 h-14 items-center justify-end border-b border-bordr bg-bgp/85 backdrop-blur px-6">
            <NotificationBell />
          </header>
          <main className="px-4 sm:px-6 md:px-8 py-6 sm:py-8 max-w-6xl mx-auto">
            <Outlet />
          </main>
          {/* Mobile nav */}
          <nav className="md:hidden fixed bottom-0 left-0 right-0 z-10 flex border-t border-bordr bg-bgs/95 backdrop-blur">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] ${
                    isActive ? 'text-brand' : 'text-inkm'
                  }`
                }
              >
                <item.icon size={18} />
                <span className="truncate">{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
}
