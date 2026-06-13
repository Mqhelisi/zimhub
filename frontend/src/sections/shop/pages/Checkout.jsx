import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ArrowLeft, ShoppingBag, MessageCircle, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';
import { useAuth } from '../../../contexts/AuthContext.jsx';
import { useCart, clearCartForSalesman } from '../hooks/useCart.js';
import { purchaseInterfaceApi } from '../../../modules/purchase_interface/api.js';

function SuccessView({ purchaseId }) {
  const [purchase, setPurchase] = useState(null);
  useEffect(() => {
    purchaseInterfaceApi.get(purchaseId).then(setPurchase).catch(() => {});
  }, [purchaseId]);
  return (
    <div className="container-page py-12">
      <Card className="text-center max-w-xl mx-auto !p-8">
        <CheckCircle2 size={42} className="mx-auto text-success" />
        <h1 className="mt-3 font-display text-3xl text-ink">Purchase initiated</h1>
        <p className="mt-2 text-inkm">
          The shop has been notified. Open the purchase to coordinate payment over WhatsApp.
        </p>
        {purchase && (
          <p className="mt-3 text-sm text-inkm">
            Reference: <span className="text-ink">#{purchase.id.slice(0, 8)}</span>
            {' • '}Total ${purchase.total_usd}
          </p>
        )}
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Link to={`/purchases/${purchaseId}`} className="btn-primary">
            <MessageCircle size={14} /> Open purchase
          </Link>
          <Link to="/shop" className="btn-secondary">
            Keep shopping
          </Link>
        </div>
      </Card>
    </div>
  );
}

export default function Checkout() {
  // Branch BEFORE any other hooks. Each sub-component owns its own hook list,
  // so React's hook-order rule is satisfied across re-renders that change the
  // URL params (e.g. after navigate('.../success')).
  const { purchaseId } = useParams();
  if (purchaseId) return <SuccessView purchaseId={purchaseId} />;
  return <CheckoutCommit />;
}

function CheckoutCommit() {
  const { salesmanId } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user, loading: authLoading } = useAuth();

  // We don't yet know the salesman snapshot here; pull it from the cart map.
  // Reading useCart with a synthetic { user_id } pulls the stored entry.
  const { cart, items, subtotal, clear } = useCart({ user_id: salesmanId });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login');
    }
  }, [authLoading, user, navigate]);

  if (authLoading || !user) {
    return <div className="container-page py-16 flex justify-center"><Spinner size={24} /></div>;
  }

  if (items.length === 0) {
    return (
      <div className="container-page py-10">
        <Link to="/shop/cart" className="text-inkm hover:text-ink text-sm inline-flex items-center gap-1">
          <ArrowLeft size={14} /> Cart
        </Link>
        <Card className="mt-6 text-center">
          <p className="text-inkm">Nothing in this shop's cart yet.</p>
          <Link to="/shop" className="mt-2 inline-block text-brand hover:underline">
            Browse the Shop →
          </Link>
        </Card>
      </div>
    );
  }

  const salesman = cart.salesman || {};
  const totalQty = items.reduce((s, i) => s + Number(i.qty), 0);

  async function placePurchase() {
    setSubmitting(true);
    try {
      const purchase = await purchaseInterfaceApi.initiate({
        listing_type: 'product',
        listing_id: items[0].product_id,
        quantity: totalQty,
        domain_payload: {
          items: items.map((it) => ({
            product_id: it.product_id,
            qty: Number(it.qty),
          })),
        },
      });
      clearCartForSalesman(salesmanId);
      toast.success('Purchase initiated. Coordinate with the shop on WhatsApp.');
      navigate(`/shop/checkout/${purchase.id}/success`, { replace: true });
    } catch (e) {
      const msg = e?.response?.data?.message || 'Could not place the purchase.';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container-page py-8">
      <Link to="/shop/cart" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Cart
      </Link>
      <h1 className="mt-3 font-display text-3xl text-ink">Confirm your order</h1>
      <p className="mt-1 text-sm text-inkm">
        Buying from <span className="text-ink">{salesman.shop_name || 'this shop'}</span>.
        You'll coordinate payment over WhatsApp after committing.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 !p-0">
          <div className="border-b border-bordr p-4 flex items-center gap-2">
            <ShoppingBag size={16} className="text-brand" />
            <h2 className="font-display text-lg text-ink">Items</h2>
          </div>
          <ul className="divide-y divide-bordr">
            {items.map((it) => (
              <li key={it.product_id} className="flex gap-3 p-3">
                {it.photo && (
                  <img src={it.photo} alt=""
                       className="h-14 w-14 rounded-md object-cover ring-1 ring-bordr" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-ink">{it.name}</div>
                  <div className="text-xs text-inkm">
                    {it.qty} × ${Number(it.price_usd).toFixed(2)}
                  </div>
                </div>
                <div className="text-sm text-ink whitespace-nowrap">
                  ${(Number(it.qty) * Number(it.price_usd)).toFixed(2)}
                </div>
              </li>
            ))}
          </ul>
          <div className="border-t border-bordr p-4 flex items-center justify-between">
            <span className="text-sm text-inkm">Total</span>
            <span className="font-display text-2xl text-ink">${subtotal.toFixed(2)}</span>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <div className="flex items-center gap-2">
              <ShieldCheck size={16} className="text-brand" />
              <h3 className="font-display text-lg text-ink">How it works</h3>
            </div>
            <ol className="mt-3 space-y-2 text-sm text-inkm">
              <li>1. You commit to buy and stock is reserved for 24h.</li>
              <li>2. You contact the shop on WhatsApp to settle payment.</li>
              <li>3. They confirm payment in ZimHub once it's received.</li>
              <li>4. You confirm receipt — purchase complete.</li>
            </ol>
          </Card>
          <Card>
            <p className="text-sm text-inkm">
              Got a problem? Raise a dispute from the purchase page and a ZimHub admin will step in.
            </p>
          </Card>

          <Button
            variant="primary"
            onClick={placePurchase}
            disabled={submitting}
            className="w-full justify-center"
          >
            <MessageCircle size={16} />
            {submitting ? 'Placing…' : `Commit to buy ($${subtotal.toFixed(2)})`}
          </Button>
        </div>
      </div>
    </div>
  );
}
