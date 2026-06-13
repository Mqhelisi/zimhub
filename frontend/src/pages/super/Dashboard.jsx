import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Inbox, MessageSquare, ShoppingBag, Ticket, Wrench, Palette, ChevronRight } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { systemApi } from '../../api/system.js';
import { formatRelative } from '../../utils/time.js';

function Stat({ icon: Icon, label, value, accent = 'brand' }) {
  return (
    <Card className="!p-4">
      <div className="flex items-center justify-between">
        <span className="label !mb-0">{label}</span>
        <Icon size={16} className={`text-${accent}`} />
      </div>
      <div className="mt-2 font-display text-3xl text-ink">{value}</div>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    systemApi.dashboardStats()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load stats.'));
    return () => { alive = false; };
  }, []);

  if (error) return <div className="text-danger">{error}</div>;
  if (!data) return <div className="flex justify-center py-10"><Spinner size={22} /></div>;

  const cap = data.users.by_capability;

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">Super Admin Dashboard</h1>
      <p className="mt-1 text-sm text-inkm">A bird's-eye view of ZimHub.</p>

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={Users} label="Total users" value={data.users.total} />
        <Stat icon={Inbox} label="Pending applications" value={data.signup_requests.pending} accent="brand" />
        <Stat icon={MessageSquare} label="Mock messages today" value={data.mock_messages_today} />
        <Stat icon={Users} label="Super admins" value={cap.is_super_admin} />
      </div>

      <h2 className="mt-10 font-display text-2xl text-ink">Sellers by category</h2>
      <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={ShoppingBag} label="Salesmen" value={cap.is_salesman} accent="shop" />
        <Stat icon={Ticket} label="Promoters" value={cap.is_promoter} accent="events" />
        <Stat icon={Wrench} label="Providers" value={cap.is_provider} accent="services" />
        <Stat icon={Palette} label="Creators" value={cap.is_creator} accent="creators" />
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <h2 className="font-display text-2xl text-ink">Quick actions</h2>
          <div className="mt-3 space-y-2">
            <Link
              to="/super/signup-requests?status=pending"
              className="card card-hover flex items-center justify-between !py-3 !px-4"
            >
              <span className="flex items-center gap-2.5 text-sm text-ink">
                <Inbox size={16} className="text-brand" /> Review pending applications
              </span>
              <ChevronRight size={16} className="text-inkm" />
            </Link>
            <Link
              to="/super/users"
              className="card card-hover flex items-center justify-between !py-3 !px-4"
            >
              <span className="flex items-center gap-2.5 text-sm text-ink">
                <Users size={16} className="text-brand" /> Manage users
              </span>
              <ChevronRight size={16} className="text-inkm" />
            </Link>
            <Link
              to="/super/mock-messages"
              className="card card-hover flex items-center justify-between !py-3 !px-4"
            >
              <span className="flex items-center gap-2.5 text-sm text-ink">
                <MessageSquare size={16} className="text-brand" /> Mock messages
              </span>
              <ChevronRight size={16} className="text-inkm" />
            </Link>
          </div>
        </div>

        <div className="lg:col-span-2">
          <h2 className="font-display text-2xl text-ink">Recent activity</h2>
          <div className="card mt-3 divide-y divide-bordr !p-0">
            {(data.recent_activity || []).length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-inkm">No recent activity.</div>
            ) : (
              data.recent_activity.map((e, i) => (
                <div key={i} className="flex items-start gap-3 px-4 py-3">
                  <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-brand/60" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-ink">{e.title}</div>
                    <div className="text-[10px] uppercase tracking-wider text-inkm/70">
                      {formatRelative(e.at)} · {e.kind.replace(/_/g, ' ')}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
