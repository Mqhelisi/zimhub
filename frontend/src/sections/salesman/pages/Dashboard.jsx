import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CreditCard, Check, AlertTriangle, DollarSign, Plus } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { formatRelative } from '../../../utils/time.js';
import { shopApi } from '../../shop/api.js';
import { PurchaseStatusBadge } from '../../../modules/purchase_interface/primitives/PurchaseStatusBadge.jsx';

function Stat({ icon: Icon, label, value, accent = 'brand', linkTo, linkLabel }) {
  return (
    <Card className="!p-4">
      <div className="flex items-center justify-between">
        <span className="label !mb-0">{label}</span>
        <Icon size={16} className={`text-${accent}`} />
      </div>
      <div className="mt-2 font-display text-3xl text-ink">{value}</div>
      {linkTo && (
        <Link to={linkTo} className="mt-1 inline-block text-xs text-brand hover:underline">
          {linkLabel} →
        </Link>
      )}
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    shopApi.admin.dashboard()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load dashboard.'));
    return () => { alive = false; };
  }, []);

  if (error) return <div className="text-danger">{error}</div>;
  if (!data) return <div className="flex justify-center py-10"><Spinner size={22} /></div>;

  const s = data.stats || {};
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-ink">Dashboard</h1>
          <p className="mt-1 text-sm text-inkm">Today at a glance.</p>
        </div>
        <Link to="/salesman/products/new">
          <Button variant="primary"><Plus size={14} /> New product</Button>
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={CreditCard} label="Pending payments (24h)" value={s.today_pending_payments ?? 0}
              linkTo="/salesman/pending-payments" linkLabel="View" />
        <Stat icon={Check} label="Completed (24h)" value={s.today_completed ?? 0} accent="success" />
        <Stat icon={AlertTriangle} label="Low-stock products" value={s.low_stock_count ?? 0} accent="warning"
              linkTo="/salesman/products?status=active" linkLabel="Review" />
        <Stat icon={DollarSign} label="Revenue (30d)" value={`$${s.revenue_30d_usd ?? '0.00'}`} accent="success" />
      </div>

      <h2 className="mt-10 font-display text-2xl text-ink heading-accent">Recent activity</h2>
      {(!data.recent_purchases || data.recent_purchases.length === 0) ? (
        <Card className="mt-4 text-center text-inkm">
          No activity yet. Once buyers commit, you'll see it here.
        </Card>
      ) : (
        <ul className="mt-4 space-y-2">
          {data.recent_purchases.map((e, i) => (
            <li key={i}>
              <Link
                to={`/purchases/${e.purchase_id}`}
                className="card flex items-center gap-3 !p-3 hover:border-brand/60"
              >
                <PurchaseStatusBadge status={e.to_status} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-ink truncate">
                    {e.note || `${e.from_status || '—'} → ${e.to_status}`}
                  </div>
                  <div className="text-xs text-inkm">
                    by {e.actor_role} • {formatRelative(e.created_at)} • ${e.total_usd}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
