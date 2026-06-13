import React from 'react';
import { NavLink, Outlet, Link, Navigate } from 'react-router-dom';
import {
  LayoutDashboard, Music2, Images, CalendarDays, UserCog, ChevronLeft,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext.jsx';
import '../../styles/theme-creators.css';

const NAV = [
  { to: '/creator', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/creator/music', label: 'Music', icon: Music2 },
  { to: '/creator/gallery', label: 'Gallery', icon: Images },
  { to: '/creator/events', label: 'Events', icon: CalendarDays },
  { to: '/creator/profile', label: 'Profile & page', icon: UserCog },
];

export default function CreatorStudioLayout() {
  const { user } = useAuth();
  if (!user?.is_creator) return <Navigate to="/" replace />;
  return (
    <div data-section="creators" className="creators-bg min-h-screen">
      <div className="border-b border-bordr/60 bg-bgs2/60">
        <div className="container-page flex items-center justify-between py-2 text-sm">
          <div className="flex items-center gap-3">
            <Link to="/" className="inline-flex items-center gap-1 text-inkm hover:text-ink">
              <ChevronLeft size={14} /> Hub
            </Link>
            <span className="font-medium text-ink">Creator Studio</span>
          </div>
          {user?.creator_profile_slug ? (
            <Link to={`/creators/${user.creator_profile_slug}`} className="text-inkm hover:text-ink">View public page →</Link>
          ) : (
            <Link to="/creators" className="text-inkm hover:text-ink">View Creators →</Link>
          )}
        </div>
      </div>
      <div className="container-page grid gap-8 py-8 lg:grid-cols-[200px,1fr]">
        <nav className="flex flex-row gap-1 overflow-x-auto lg:flex-col">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to} to={to} end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition ${
                  isActive ? 'bg-[rgb(var(--section-accent)/0.15)] text-ink' : 'text-inkm hover:bg-bgs2 hover:text-ink'
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
