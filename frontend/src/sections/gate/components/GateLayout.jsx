import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { LogOut, ScanLine } from 'lucide-react';
import { GateAuthProvider, useGateAuth } from '../context/GateAuthContext.jsx';
import '../../events/theme/theme-events.css';

function TopBar() {
  const { meta, logout } = useGateAuth();
  if (!meta) return null;
  return (
    <div className="bg-bgs2/80 border-b border-bordr/60 backdrop-blur sticky top-0 z-30">
      <div className="px-4 py-2 flex items-center justify-between gap-2 text-sm">
        <div className="min-w-0">
          <div className="text-ink font-medium truncate">{meta.event?.title}</div>
          <div className="text-xs text-inkm truncate">
            Gateman: {meta.gateman?.name} • scans: {meta.gateman?.scan_count ?? 0}
          </div>
        </div>
        <button onClick={logout} className="btn-ghost"><LogOut size={14} /> Sign out</button>
      </div>
    </div>
  );
}

function GateShell() {
  return (
    <div data-section="events" className="events-bg min-h-screen flex flex-col">
      <TopBar />
      <Outlet />
    </div>
  );
}

export default function GateLayout() {
  return (
    <GateAuthProvider>
      <GateShell />
    </GateAuthProvider>
  );
}
