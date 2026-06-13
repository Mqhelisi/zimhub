import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Minus, Plus, ShoppingCart, Store, ChevronLeft } from 'lucide-react';
import { Card, Spinner } from '../../../components/ui/Card.jsx';
import { Button } from '../../../components/ui/Button.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';
import { useAuth } from '../../../contexts/AuthContext.jsx';
import { shopApi } from '../api.js';
import { useCart } from '../hooks/useCart.js';

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [error, setError] = useState('');
  const [activePhoto, setActivePhoto] = useState(0);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    let alive = true;
    setProduct(null); setError('');
    shopApi.productDetail(id)
      .then((p) => alive && setProduct(p))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load product.'));
    return () => { alive = false; };
  }, [id]);

  const { addItem } = useCart(product?.salesman || null);

  if (error) {
    return (
      <div className="container-page py-10">
        <Link to="/shop" className="text-inkm hover:text-ink inline-flex items-center gap-1 text-sm">
          <ChevronLeft size={14} /> Back to shop
        </Link>
        <p className="mt-4 text-danger">{error}</p>
      </div>
    );
  }
  if (!product) return <div className="container-page py-16 flex justify-center"><Spinner size={24} /></div>;

  const photos = product.photos || [];
  const available = Number(product.available ?? 0);
  const soldOut = available === 0;
  const ownedByMe = user && String(user.id) === String(product.salesman?.user_id);

  function handleAdd() {
    if (!user) {
      toast.error('Sign in or sign up to buy.');
      navigate('/login');
      return;
    }
    if (ownedByMe) {
      toast.error('You can\'t buy from your own shop.');
      return;
    }
    if (soldOut) return;
    addItem({
      id: product.id,
      name: product.name,
      price_usd: product.price_usd,
      photos: product.photos,
      available,
    }, qty);
    toast.success(`Added to cart: ${product.name} × ${qty}`);
  }

  return (
    <div className="container-page py-6">
      <Link to={`/shop/salesman/${product.salesman?.shop_slug || ''}`}
            className="text-inkm hover:text-ink inline-flex items-center gap-1 text-sm">
        <ChevronLeft size={14} /> {product.salesman?.shop_name || 'Shop'}
      </Link>

      <div className="mt-4 grid gap-6 lg:grid-cols-2">
        <div>
          <div className="aspect-[4/3] w-full overflow-hidden rounded-lg bg-bgs2 ring-1 ring-bordr">
            {photos[activePhoto] ? (
              <img src={photos[activePhoto]} alt={product.name} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-inkm">No image</div>
            )}
          </div>
          {photos.length > 1 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {photos.map((p, i) => (
                <button
                  key={i}
                  onClick={() => setActivePhoto(i)}
                  className={`h-14 w-14 overflow-hidden rounded-md ring-1 transition ${
                    i === activePhoto ? 'ring-brand' : 'ring-bordr hover:ring-inkm'
                  }`}
                >
                  <img src={p} alt="" className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <h1 className="font-display text-3xl text-ink">{product.name}</h1>
          {product.salesman && (
            <Link
              to={`/shop/salesman/${product.salesman.shop_slug}`}
              className="mt-1 inline-flex items-center gap-1 text-sm text-brand hover:underline"
            >
              <Store size={12} /> {product.salesman.shop_name}
            </Link>
          )}

          <div className="mt-4 flex items-baseline gap-3">
            <div className="font-display text-3xl text-brand">
              ${Number(product.price_usd).toFixed(2)}
            </div>
            <span className="text-xs text-inkm uppercase tracking-wider">{product.currency || 'USD'}</span>
          </div>

          <div className="mt-2 text-sm">
            {soldOut ? (
              <span className="text-danger">Sold out</span>
            ) : available <= 3 ? (
              <span className="text-warning">Only {available} left</span>
            ) : (
              <span className="text-inkm">{available} available</span>
            )}
          </div>

          <p className="mt-4 text-ink whitespace-pre-wrap">{product.description}</p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center rounded-md border border-bordr">
              <button
                onClick={() => setQty((q) => Math.max(1, q - 1))}
                className="p-2 text-inkm hover:text-ink disabled:opacity-40"
                disabled={qty <= 1 || soldOut}
              >
                <Minus size={14} />
              </button>
              <input
                type="number" min={1} max={Math.max(1, available)} value={qty}
                onChange={(e) => setQty(Math.max(1, Math.min(available || 1, Number(e.target.value) || 1)))}
                className="w-12 bg-transparent text-center text-sm text-ink"
              />
              <button
                onClick={() => setQty((q) => Math.min(available, q + 1))}
                className="p-2 text-inkm hover:text-ink disabled:opacity-40"
                disabled={qty >= available || soldOut}
              >
                <Plus size={14} />
              </button>
            </div>
            <Button variant="primary" onClick={handleAdd} disabled={soldOut || ownedByMe}>
              <ShoppingCart size={16} /> {ownedByMe ? 'Your shop' : soldOut ? 'Sold out' : 'Add to cart'}
            </Button>
          </div>

          <Card className="mt-6 !bg-bgs2/40">
            <p className="text-sm text-inkm">
              <span className="text-ink font-medium">How ZimHub purchases work:</span>{' '}
              When you commit to buy, the Salesman is notified and you coordinate on WhatsApp.
              You pay them via Ecocash (or whatever you agree on). They confirm payment in ZimHub
              and prepare your goods. You confirm receipt to close the loop. If anything goes wrong,
              raise a dispute and an admin steps in.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
