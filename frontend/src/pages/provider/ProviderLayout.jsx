// Provider admin chrome — sidebar nav nested inside the Services theme.
// Mirrors the Salesman/Promoter layout pattern from Stages 2–3.
import React from 'react';
import { NavLink, Outlet, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import {
  LayoutDashboard, Wrench, CalendarDays, CalendarClock, Inbox, UserCog,
  ChevronLeft,
} from 'lucide-react';
import '../../styles/theme-services.css';

const NAV = [
  { to: '/provider', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/provider/services', label: 'My services', icon: Wrench },
  { to: '/provider/requests', label: 'Requests', icon: Inbox },
  { to: '/provider/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/provider/availability', label: 'Availability', icon: CalendarClock },
  { to: '/provider/profile', label: 'Profile', icon: UserCog },
];

export default function ProviderLayout() {
  const { user } = useAuth();
  // Capability guard — mirrors SalesmanLayout/PromoterLayout (Stages 2–3).
  if (!user?.is_provider) return <Navigate to="/" replace />;
  return (
    <div data-section="services" className="services-bg min-h-screen">
      <div className="border-b border-bordr/60 bg-bgs2/60">
        <div className="container-page flex items-center justify-between py-2 text-sm">
          <div className="flex items-center gap-3">
            <Link to="/" className="inline-flex items-center gap-1 text-inkm hover:text-ink">
              <ChevronLeft size={14} /> Hub
            </Link>
            <span className="font-medium text-ink">Provider admin</span>
          </div>
          <Link to="/services" className="text-inkm hover:text-ink">View public Services →</Link>
        </div>
      </div>
      <div className="container-page grid gap-8 py-8 lg:grid-cols-[200px,1fr]">
        <nav className="flex flex-row gap-1 overflow-x-auto lg:flex-col">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-[rgb(var(--section-accent)/0.15)] text-ink'
                    : 'text-inkm hover:bg-bgs2 hover:text-ink'
                }`
              }
            >
              <Icon size={16} /> {label}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0"><Outlet /></main>
      </div>
    </div>
  );
}
