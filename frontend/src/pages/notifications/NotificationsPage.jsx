import React from 'react';
import { CheckCheck, Bell } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useNotifications } from '../../contexts/NotificationsContext.jsx';
import { formatDateTime } from '../../utils/time.js';
import { notificationLink } from '../../utils/notificationLinks.js';
import { Card } from '../../components/ui/Card.jsx';
import { Badge } from '../../components/ui/Badge.jsx';

function groupByDate(notifications) {
  const groups = new Map();
  for (const n of notifications) {
    const key = (n.created_at || '').slice(0, 10);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(n);
  }
  return Array.from(groups.entries());
}

const KIND_TONE = {
  seller_application_approved: 'success',
  seller_application_rejected: 'danger',
  new_signup_request: 'brand',
  password_reset_requested: 'warning',
  welcome: 'brand',
  announcement: 'default',
};

export default function NotificationsPage() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const grouped = groupByDate(notifications);

  return (
    <div className="container-narrow">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl text-ink">Notifications</h1>
          <p className="mt-1 text-sm text-inkm">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button onClick={() => markAllRead()} className="btn-secondary">
            <CheckCheck size={16} /> Mark all read
          </button>
        )}
      </div>

      <div className="mt-6 space-y-6">
        {notifications.length === 0 && (
          <Card className="text-center">
            <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-bgs2 text-inkm">
              <Bell size={22} />
            </div>
            <p className="mt-3 text-sm text-inkm">No notifications yet.</p>
          </Card>
        )}
        {grouped.map(([date, items]) => (
          <div key={date}>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-inkm">
              {formatDateTime(date + 'T00:00:00Z').split(',')[0]}
            </h3>
            <div className="card divide-y divide-bordr">
              {items.map((n) => {
                const to = notificationLink(n);
                const rowCls = `block w-full text-left px-4 py-3 transition hover:bg-bgs2 ${
                  !n.read_at ? 'bg-brand/[0.05]' : ''
                }`;
                const inner = (
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Badge tone={KIND_TONE[n.kind] || 'default'}>{n.kind.replace(/_/g, ' ')}</Badge>
                        {!n.read_at && <span className="h-1.5 w-1.5 rounded-full bg-brand" />}
                      </div>
                      <h4 className="mt-1.5 text-sm font-semibold text-ink">{n.title}</h4>
                      <p className="mt-0.5 text-sm text-inkm">{n.body}</p>
                    </div>
                    <div className="shrink-0 text-[10px] uppercase tracking-wider text-inkm/70">
                      {formatDateTime(n.created_at)}
                    </div>
                  </div>
                );
                if (to) {
                  return (
                    <Link
                      key={n.id}
                      to={to}
                      onClick={() => !n.read_at && markRead(n.id)}
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
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
