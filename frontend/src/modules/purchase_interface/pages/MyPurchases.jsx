import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ShoppingBag, ArrowRight } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { formatRelative } from '../../../utils/time.js';
import { purchaseInterfaceApi, STATUS_LABELS } from '../api.js';
import { PurchaseStatusBadge } from '../primitives/PurchaseStatusBadge.jsx';

const TABS = [
  { key: '', label: 'All' },
  { key: 'awaiting_payment', label: 'To pay' },
  { key: 'awaiting_buyer_confirmation', label: 'To confirm' },
  { key: 'completed', label: 'Completed' },
  { key: 'disputed', label: 'Disputed' },
];

export default function MyPurchases() {
  const [purchases, setPurchases] = useState(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');

  useEffect(() => {
    let alive = true;
    setPurchases(null);
    purchaseInterfaceApi.myPurchases({ role: 'buyer', status: filter || undefined })
      .then((rows) => alive && setPurchases(rows))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load purchases.'));
    return () => { alive = false; };
  }, [filter]);

  return (
    <div className="container-page py-8">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl text-ink">My purchases</h1>
          <p className="mt-1 text-sm text-inkm">Everything you've initiated on ZimHub.</p>
        </div>
        <Link to="/shop" className="text-sm text-brand hover:underline inline-flex items-center gap-1">
          Keep shopping <ArrowRight size={14} />
        </Link>
      </div>

      <div className="mt-5 flex flex-wrap gap-2 border-b border-bordr pb-3">
        {TABS.map((t) => (
          <button
            key={t.key || 'all'}
            onClick={() => setFilter(t.key)}
            className={`rounded-full px-3 py-1 text-sm transition
              ${filter === t.key
                ? 'bg-brand text-bg'
                : 'text-inkm hover:bg-bgs2 hover:text-ink'
              }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="mt-6 text-danger">{error}</div>}
      {!purchases && !error && (
        <div className="mt-10 flex justify-center"><Spinner size={22} /></div>
      )}
      {purchases && purchases.length === 0 && (
        <Card className="mt-6 text-center">
          <ShoppingBag size={28} className="mx-auto text-inkm" />
          <p className="mt-2 text-inkm">
            {filter
              ? `No purchases ${STATUS_LABELS[filter]?.toLowerCase() || ''}.`
              : 'You haven\'t made any purchases yet.'}
          </p>
          <Link to="/shop" className="mt-3 inline-block text-brand hover:underline">
            Browse the Shop →
          </Link>
        </Card>
      )}
      {purchases && purchases.length > 0 && (
        <ul className="mt-6 space-y-3">
          {purchases.map((p) => {
            const item = (p.domain_payload?.items || [])[0];
            return (
              <li key={p.id}>
                <Link
                  to={`/purchases/${p.id}`}
                  className="card flex items-center gap-3 p-4 hover:border-brand/60 transition"
                >
                  {item?.photo && (
                    <img src={item.photo} alt=""
                         className="h-14 w-14 shrink-0 rounded-md object-cover ring-1 ring-bordr" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-ink">
                      {item?.name || 'Purchase'}{
                        (p.domain_payload?.items || []).length > 1 &&
                        <span className="text-inkm font-normal"> +{p.domain_payload.items.length - 1} more</span>
                      }
                    </div>
                    <div className="text-xs text-inkm">
                      {p.seller?.shop_name || p.seller?.name} • {formatRelative(p.created_at)}
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
