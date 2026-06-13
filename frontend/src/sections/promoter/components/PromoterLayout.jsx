import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Calendar, UserCircle2, ChevronLeft } from 'lucide-react';
import '../../events/theme/theme-events.css';

const NAV = [
  { to: '/promoter', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/promoter/events', label: 'Events', icon: Calendar },
  { to: '/promoter/profile', label: 'Profile', icon: UserCircle2 },
];

export default function PromoterLayout() {
  const { pathname } = useLocation();
  return (
    <div data-section="events" className="events-bg min-h-screen">
      <div className="bg-bgs2/60 border-b border-bordr/60">
        <div className="container-page py-2 flex items-center justify-between gap-3 text-sm">
          <Link to="/" className="text-inkm hover:text-ink inline-flex items-center gap-1">
            <ChevronLeft size={14} /> Hub
          </Link>
          <nav className="flex items-center gap-1">
            {NAV.map((n) => {
              const Icon = n.icon;
              const active = n.exact ? pathname === n.to : pathname.startsWith(n.to);
              return (
                <Link key={n.to} to={n.to}
                  className={`px-3 py-1.5 rounded-md inline-flex items-center gap-1.5 ${
                    active ? 'text-ink bg-bgs' : 'text-inkm hover:text-ink hover:bg-bgs'
                  }`}>
                  <Icon size={14} /> {n.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="events-divider sm" />
      </div>
      <Outlet />
    </div>
  );
}
