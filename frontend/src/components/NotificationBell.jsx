import React, { useState, useRef, useEffect } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useNotifications } from '../contexts/NotificationsContext.jsx';
import { formatRelative } from '../utils/time.js';
import { notificationLink } from '../utils/notificationLinks.js';

export function NotificationBell() {
  const { notifications, unreadCount, markAllRead, markRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const recent = (notifications || []).slice(0, 5);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg border border-bordr bg-bgs2 p-2 text-inkm hover:text-ink hover:border-brand/40 transition"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand px-1 text-[10px] font-bold text-[rgb(20_15_8)]">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 card p-0 shadow-2xl">
          <div className="flex items-center justify-between border-b border-bordr px-4 py-2.5">
            <div className="font-display text-base text-ink">Notifications</div>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllRead()}
                className="flex items-center gap-1 text-xs text-inkm hover:text-brand transition"
              >
                <CheckCheck size={13} /> Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {recent.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-inkm">
                No notifications yet.
              </div>
            ) : (
              recent.map((n) => {
                const to = notificationLink(n);
                const rowCls = `block w-full border-b border-bordr px-4 py-3 text-left transition hover:bg-bgs2 ${
                  !n.read_at ? 'bg-brand/[0.04]' : ''
                }`;
                const inner = (
                  <>
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-sm font-semibold text-ink">{n.title}</div>
                      {!n.read_at && <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />}
                    </div>
                    <div className="mt-0.5 line-clamp-2 text-xs text-inkm">{n.body}</div>
                    <div className="mt-1 text-[10px] uppercase tracking-wider text-inkm/70">
                      {formatRelative(n.created_at)}
                    </div>
                  </>
                );
                if (to) {
                  return (
                    <Link
                      key={n.id}
                      to={to}
                      onClick={() => { if (!n.read_at) markRead(n.id); setOpen(false); }}
                      className={rowCls}
                    >
                      {inner}
                    </Link>
                  );
                }
                return (
                  <button
                    key={n.id}
                    onClick={() => !n.read_at && markRead(n.id)}
                    className={rowCls}
                  >
                    {inner}
                  </button>
                );
              })
            )}
          </div>
          <Link
            to="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-bordr px-4 py-2.5 text-center text-sm text-brand hover:text-brand-hover"
          >
            View all notifications →
          </Link>
        </div>
      )}
    </div>
  );
}
