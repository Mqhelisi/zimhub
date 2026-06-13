import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Music2, ChevronLeft, Ticket } from 'lucide-react';
import '../theme/theme-events.css';

export default function EventsSectionLayout() {
  const { pathname } = useLocation();
  const onLanding = pathname === '/events' || pathname === '/events/';
  return (
    <div data-section="events" className="events-bg min-h-screen">
      <div className="bg-bgs2/60 border-b border-bordr/60">
        <div className="container-page py-2 flex items-center justify-between gap-3 text-sm">
          <div className="flex items-center gap-3 min-w-0">
            {!onLanding && (
              <Link to="/" className="text-inkm hover:text-ink inline-flex items-center gap-1">
                <ChevronLeft size={14} /> Hub
              </Link>
            )}
            <Link to="/events" className="text-ink inline-flex items-center gap-2 font-medium min-w-0">
              <Music2 size={16} className="text-brand shrink-0" />
              <span className="truncate">ZimHub Events</span>
            </Link>
          </div>
          <Link
            to="/my/tickets"
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-inkm hover:text-ink hover:bg-bgs2"
          >
            <Ticket size={16} /> My tickets
          </Link>
        </div>
        <div className="events-divider sm" />
      </div>
      <Outlet />
    </div>
  );
}
