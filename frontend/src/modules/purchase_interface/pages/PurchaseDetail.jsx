import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, ShoppingBag, User as UserIcon, Clock } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { useAuth } from '../../../contexts/AuthContext.jsx';
import { formatRelative } from '../../../utils/time.js';
import { purchaseInterfaceApi } from '../api.js';
import { PurchaseStatusBadge } from '../primitives/PurchaseStatusBadge.jsx';
import { PurchaseProgress } from '../primitives/PurchaseProgress.jsx';
import { PurchaseActions } from '../primitives/PurchaseActions.jsx';
import { PurchaseEventTimeline } from '../primitives/PurchaseEventTimeline.jsx';
import { DisputeBanner } from '../primitives/DisputeBanner.jsx';

export default function PurchaseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [purchase, setPurchase] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    purchaseInterfaceApi.get(id)
      .then((p) => alive && setPurchase(p))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load purchase.'));
    return () => { alive = false; };
  }, [id]);

  if (error) {
    return (
      <div className="container-page py-10">
        <Link to="/my/purchases" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
          <ArrowLeft size={14} /> Back to purchases
        </Link>
        <p className="mt-4 text-danger">{error}</p>
      </div>
    );
  }
  if (!purchase) {
    return <div className="container-page py-10 flex justify-center"><Spinner size={22} /></div>;
  }

  const isBuyer = user && String(user.id) === String(purchase.buyer_id);
  const isSeller = user && String(user.id) === String(purchase.seller_id);
  const counterparty = isBuyer ? purchase.seller : isSeller ? purchase.buyer : null;
  const items = (purchase.domain_payload && purchase.domain_payload.items) || [];

  return (
    <div className="container-page py-8">
      <div className="flex items-center justify-between">
        <Link
          to={isSeller ? '/salesman/pending-payments' : '/my/purchases'}
          className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1"
        >
          <ArrowLeft size={14} /> Back
        </Link>
        <PurchaseStatusBadge status={purchase.status} />
      </div>

      <h1 className="mt-3 font-display text-3xl text-ink">
        Purchase <span className="text-inkm text-2xl">#{purchase.id.slice(0, 8)}</span>
      </h1>

      <div className="mt-6">
        <PurchaseProgress purchase={purchase} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {purchase.dispute && <DisputeBanner dispute={purchase.dispute} />}

          <Card>
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-xl text-ink flex items-center gap-2">
                <ShoppingBag size={18} className="text-brand" /> Items
              </h2>
              <span className="text-sm text-inkm">{purchase.quantity} unit{purchase.quantity !== 1 ? 's' : ''}</span>
            </div>
            <ul className="mt-3 divide-y divide-bordr">
              {items.map((it, idx) => (
                <li key={idx} className="flex gap-3 py-3">
                  {it.photo && (
                    <img
                      src={it.photo} alt="" loading="lazy"
                      className="h-14 w-14 rounded-md object-cover ring-1 ring-bordr"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-ink truncate">{it.name || 'Item'}</div>
                    <div className="text-xs text-inkm">
                      {it.qty} × ${Number(it.unit_price_usd || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="text-sm text-ink whitespace-nowrap">
                    ${(Number(it.unit_price_usd || 0) * Number(it.qty || 1)).toFixed(2)}
                  </div>
                </li>
              ))}
              {items.length === 0 && (
                <li className="py-3 text-sm text-inkm">
                  No line items recorded; total ${purchase.total_usd}.
                </li>
              )}
            </ul>
            <div className="mt-3 flex items-center justify-between border-t border-bordr pt-3">
              <span className="text-sm text-inkm">Total</span>
              <span className="font-display text-2xl text-ink">${purchase.total_usd}</span>
            </div>
          </Card>

          <Card>
            <h2 className="font-display text-xl text-ink">Activity</h2>
            <div className="mt-3">
              <PurchaseEventTimeline events={purchase.events || []} />
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <h2 className="font-display text-xl text-ink flex items-center gap-2">
              <UserIcon size={18} className="text-brand" />
              {isBuyer ? 'Seller' : isSeller ? 'Buyer' : 'Parties'}
            </h2>
            {counterparty ? (
              <div className="mt-3">
                <div className="font-medium text-ink">{counterparty.name}</div>
                {counterparty.shop_name && (
                  <Link
                    to={`/shop/salesman/${counterparty.shop_slug || ''}`}
                    className="text-xs text-brand hover:underline"
                  >
                    {counterparty.shop_name}
                  </Link>
                )}
                <div className="mt-1 text-sm text-inkm">{counterparty.phone}</div>
                {counterparty.email && (
                  <div className="text-sm text-inkm">{counterparty.email}</div>
                )}
              </div>
            ) : (
              <div className="mt-3 text-sm text-inkm">
                <div>Buyer: {purchase.buyer?.name}</div>
                <div>Seller: {purchase.seller?.shop_name || purchase.seller?.name}</div>
              </div>
            )}
          </Card>

          {(purchase.hold_expires_at || purchase.auto_complete_at) && (
            <Card>
              <h2 className="font-display text-xl text-ink flex items-center gap-2">
                <Clock size={18} className="text-brand" /> Timing
              </h2>
              <div className="mt-3 space-y-2 text-sm">
                {purchase.status === 'awaiting_payment' && purchase.hold_expires_at && (
                  <div className="text-inkm">
                    Hold expires <span className="text-ink">{formatRelative(purchase.hold_expires_at)}</span>.
                  </div>
                )}
                {purchase.status === 'awaiting_buyer_confirmation' && purchase.auto_complete_at && (
                  <div className="text-inkm">
                    Auto-completes <span className="text-ink">{formatRelative(purchase.auto_complete_at)}</span>
                    {' '}if the buyer doesn't confirm.
                  </div>
                )}
                {purchase.payment_ref && (
                  <div className="text-inkm">
                    Payment ref: <span className="text-ink">{purchase.payment_ref}</span>
                  </div>
                )}
              </div>
            </Card>
          )}

          <Card>
            <h2 className="font-display text-xl text-ink">What you can do</h2>
            <div className="mt-3">
              <PurchaseActions purchase={purchase} onChanged={setPurchase} />
            </div>
            {(purchase.permitted_actions || []).length === 0 && (
              <p className="mt-3 text-sm text-inkm">
                No actions available from this status.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
