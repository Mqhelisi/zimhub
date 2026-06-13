import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Palette, ChevronLeft } from 'lucide-react';
import '../../styles/theme-creators.css';

export default function CreatorsSectionLayout() {
  const { pathname } = useLocation();
  const onLanding = pathname === '/creators' || pathname === '/creators/';
  return (
    <div data-section="creators" className="creators-bg min-h-screen">
      <div className="border-b border-bordr/60 bg-bgs2/50">
        <div className="container-page flex items-center justify-between gap-3 py-2 text-sm">
          <div className="flex min-w-0 items-center gap-3">
            {!onLanding && (
              <Link to="/" className="inline-flex items-center gap-1 text-inkm hover:text-ink">
                <ChevronLeft size={14} /> Hub
              </Link>
            )}
            <Link to="/creators" className="inline-flex min-w-0 items-center gap-2 font-medium text-ink">
              <Palette size={16} className="shrink-0" style={{ color: 'rgb(var(--section-accent))' }} />
              <span className="truncate">ZimHub Creators</span>
            </Link>
          </div>
        </div>
      </div>
      <Outlet />
    </div>
  );
}
