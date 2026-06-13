import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, Trash2, Plus, Minus, Store, ArrowRight } from 'lucide-react';
import { Card } from '../../../components/ui/Card.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { useAllCarts, useCart } from '../hooks/useCart.js';
import { useAuth } from '../../../contexts/AuthContext.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';

function SalesmanCartSection({ entry }) {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const { items, setQty, removeItem, subtotal } = useCart(entry.salesman);

  function handleCheckout() {
    if (!user) {
      toast.error('Sign in to check out.');
      navigate('/login');
      return;
    }
    navigate(`/shop/checkout/${entry.salesmanId}`);
  }

  if (items.length === 0) return null;

  return (
    <Card className="!p-0 overflow-hidden">
      <div className="flex items-center gap-3 border-b border-bordr p-3">
        {entry.salesman?.photo_url ? (
          <img src={entry.salesman.photo_url} alt=""
               className="h-9 w-9 rounded-full object-cover ring-1 ring-bordr" />
        ) : (
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-bgs2 text-brand">
            <Store size={14} />
          </div>
        )}
        <Link
          to={`/shop/salesman/${entry.salesman?.shop_slug || ''}`}
          className="font-medium text-ink hover:underline truncate"
        >
          {entry.salesman?.shop_name || 'Shop'}
        </Link>
      </div>

      <ul className="divide-y divide-bordr">
        {items.map((it) => (
          <li key={it.product_id} className="flex gap-3 p-3">
            {it.photo && (
              <img src={it.photo} alt=""
                   className="h-16 w-16 shrink-0 rounded-md object-cover ring-1 ring-bordr" />
            )}
            <div className="min-w-0 flex-1">
              <Link
                to={`/shop/product/${it.product_id}`}
                className="block truncate text-ink hover:underline"
              >
                {it.name}
              </Link>
              <div className="mt-0.5 text-xs text-inkm">
                ${Number(it.price_usd).toFixed(2)} each
              </div>
              <div className="mt-2 flex items-center gap-3">
                <div className="inline-flex items-center rounded-md border border-bordr">
                  <button
                    onClick={() => setQty(it.product_id, it.qty - 1)}
                    className="p-1.5 text-inkm hover:text-ink"
                  >
                    <Minus size={12} />
                  </button>
                  <span className="px-2 text-sm text-ink min-w-[2ch] text-center">{it.qty}</span>
                  <button
                    onClick={() => setQty(it.product_id, Math.min(it.available || 999, it.qty + 1))}
                    className="p-1.5 text-inkm hover:text-ink"
                  >
                    <Plus size={12} />
                  </button>
                </div>
                <button
                  onClick={() => removeItem(it.product_id)}
                  className="text-xs text-danger inline-flex items-center gap-0.5 hover:underline"
                >
                  <Trash2 size={12} /> Remove
                </button>
              </div>
            </div>
            <div className="text-sm text-ink whitespace-nowrap">
              ${(Number(it.qty) * Number(it.price_usd)).toFixed(2)}
            </div>
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between border-t border-bordr p-3">
        <div>
          <div className="text-xs text-inkm">Subtotal for this shop</div>
          <div className="font-display text-2xl text-ink">${subtotal.toFixed(2)}</div>
        </div>
        <Button variant="primary" onClick={handleCheckout}>
          Check out <ArrowRight size={14} />
        </Button>
      </div>
    </Card>
  );
}

export default function Cart() {
  const { carts, totalUsd } = useAllCarts();
  return (
    <div className="container-page py-8">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="font-display text-3xl text-ink">Your cart</h1>
          <p className="mt-1 text-sm text-inkm">
            ZimHub places one purchase per shop. Each shop checks out separately.
          </p>
        </div>
        <Link to="/shop" className="text-sm text-brand hover:underline">Keep shopping →</Link>
      </div>

      {carts.length === 0 ? (
        <Card className="mt-8 text-center">
          <ShoppingCart size={28} className="mx-auto text-inkm" />
          <p className="mt-2 text-inkm">Your cart is empty.</p>
          <Link to="/shop" className="mt-3 inline-block text-brand hover:underline">
            Browse the Shop →
          </Link>
        </Card>
      ) : (
        <>
          <div className="mt-6 space-y-4">
            {carts.map((c) => (
              <SalesmanCartSection key={c.salesmanId} entry={c} />
            ))}
          </div>
          <div className="mt-6 flex items-center justify-end gap-3">
            <div className="text-sm text-inkm">Cart total across all shops</div>
            <div className="font-display text-2xl text-ink">${totalUsd.toFixed(2)}</div>
          </div>
        </>
      )}
    </div>
  );
}
