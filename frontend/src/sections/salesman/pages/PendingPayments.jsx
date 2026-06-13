import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CreditCard, Clock } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { formatRelative } from '../../../utils/time.js';
import { purchaseInterfaceApi } from '../../../modules/purchase_interface/api.js';
import { PurchaseStatusBadge } from '../../../modules/purchase_interface/primitives/PurchaseStatusBadge.jsx';

const TABS = [
  { key: 'awaiting_payment', label: 'Awaiting payment' },
  { key: 'awaiting_buyer_confirmation', label: 'Awaiting confirmation' },
  { key: 'disputed', label: 'Disputed' },
  { key: 'completed', label: 'Completed' },
];

export default function PendingPayments() {
  const [tab, setTab] = useState('awaiting_payment');
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setRows(null); setError('');
    purchaseInterfaceApi.myPurchases({ role: 'seller', status: tab, listing_type: 'product' })
      .then((r) => alive && setRows(r))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load purchases.'));
    return () => { alive = false; };
  }, [tab]);

  return (
    <div>
      <div className="flex items-baseline gap-2">
        <CreditCard size={18} className="text-brand" />
        <h1 className="font-display text-3xl text-ink">Purchases</h1>
      </div>
      <p className="mt-1 text-sm text-inkm">
        Coordinate with buyers on WhatsApp, confirm payments here.
      </p>

      <div className="mt-5 flex flex-wrap gap-2 border-b border-bordr pb-3">
        {TABS.map((t) => (
          <button
            key={t.key} onClick={() => setTab(t.key)}
            className={`rounded-full px-3 py-1 text-sm transition
              ${tab === t.key ? 'bg-brand text-bg' : 'text-inkm hover:bg-bgs2 hover:text-ink'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="mt-6 text-danger">{error}</div>}
      {!rows && !error && <div className="mt-10 flex justify-center"><Spinner size={22} /></div>}
      {rows && rows.length === 0 && (
        <Card className="mt-6 text-center text-inkm">
          Nothing in this state right now.
        </Card>
      )}
      {rows && rows.length > 0 && (
        <ul className="mt-5 space-y-2">
          {rows.map((p) => {
            const items = p.domain_payload?.items || [];
            const item = items[0];
            const extra = items.length > 1 ? ` +${items.length - 1} more` : '';
            return (
              <li key={p.id}>
                <Link
                  to={`/purchases/${p.id}`}
                  className="card flex items-center gap-3 !p-3 hover:border-brand/60"
                >
                  {item?.photo && (
                    <img src={item.photo} alt=""
                         className="h-12 w-12 shrink-0 rounded-md object-cover ring-1 ring-bordr" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-ink">
                      {item?.name || 'Purchase'}{extra}
                    </div>
                    <div className="text-xs text-inkm">
                      {p.buyer?.name} • {formatRelative(p.created_at)}
                      {p.hold_expires_at && p.status === 'awaiting_payment' && (
                        <span className="ml-1 text-warning">
                          <Clock size={10} className="inline-block" /> expires {formatRelative(p.hold_expires_at)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <PurchaseStatusBadge status={p.status} />
                    <div className="mt-1 text-sm text-ink">${p.total_usd}</div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
