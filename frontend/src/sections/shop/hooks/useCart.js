// useCart — per-Salesman cart stored in localStorage.
//
// Per spec: ONE Purchase per Salesman per checkout. So we shard carts by
// salesman_user_id. The hook surfaces helpers for one salesman at a time
// but also exposes top-level totals across all salesman carts (for the
// CartIcon badge).
//
// Storage shape:
//   localStorage["zimhub:cart:v1"] = JSON {
//     "<salesman_user_id>": {
//       salesman: { user_id, shop_name, shop_slug, photo_url },
//       items: [{ product_id, name, price_usd, photo, qty, available }],
//       updated_at: <iso>
//     }
//   }
//
// We re-read the whole map on every read so multiple tabs / windows stay
// roughly in sync (also via the storage event listener).
import { useCallback, useEffect, useState } from 'react';

const KEY = 'zimhub:cart:v1';

function readMap() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeMap(map) {
  try {
    localStorage.setItem(KEY, JSON.stringify(map || {}));
    // Notify listeners in same tab (storage event only fires across tabs).
    window.dispatchEvent(new CustomEvent('zimhub:cart:changed'));
  } catch {
    /* quota / privacy mode — noop */
  }
}

// Subscribe to cart changes and re-render
function useCartTick() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const handler = () => setTick((n) => n + 1);
    window.addEventListener('storage', handler);
    window.addEventListener('zimhub:cart:changed', handler);
    return () => {
      window.removeEventListener('storage', handler);
      window.removeEventListener('zimhub:cart:changed', handler);
    };
  }, []);
  return tick;
}

// --- Public top-level helpers --------------------------------------
export function useAllCarts() {
  useCartTick(); // re-render on change
  const map = readMap();
  const entries = Object.entries(map).filter(([, c]) => (c?.items?.length || 0) > 0);

  const totalUnits = entries.reduce(
    (sum, [, c]) => sum + c.items.reduce((s, i) => s + Number(i.qty || 0), 0),
    0,
  );
  const totalUsd = entries.reduce(
    (sum, [, c]) =>
      sum + c.items.reduce((s, i) => s + Number(i.qty || 0) * Number(i.price_usd || 0), 0),
    0,
  );
  return {
    carts: entries.map(([salesmanId, c]) => ({ salesmanId, ...c })),
    totalUnits,
    totalUsd,
  };
}

export function useCart(salesman /* { user_id, shop_name, shop_slug, photo_url } */) {
  useCartTick();
  const salesmanId = salesman?.user_id;

  const cart = (readMap()[salesmanId] || { salesman: salesman || null, items: [] });

  const addItem = useCallback((product, qty = 1) => {
    if (!salesmanId) return;
    const map = readMap();
    const c = map[salesmanId] || { salesman, items: [], updated_at: null };
    // Update salesman snapshot on every add (in case it changed)
    c.salesman = salesman || c.salesman;

    const existing = c.items.find((i) => i.product_id === product.id);
    const stockCap = Math.max(0, Number(product.available ?? product.stock_quantity ?? 999));
    if (existing) {
      existing.qty = Math.min(stockCap, Number(existing.qty || 0) + Number(qty));
    } else {
      c.items.push({
        product_id: product.id,
        name: product.name,
        price_usd: String(product.price_usd),
        photo: (product.photos || [null])[0] || null,
        qty: Math.min(stockCap, Number(qty)),
        available: stockCap,
      });
    }
    c.updated_at = new Date().toISOString();
    map[salesmanId] = c;
    writeMap(map);
  }, [salesmanId, salesman]);

  const setQty = useCallback((productId, qty) => {
    if (!salesmanId) return;
    const map = readMap();
    const c = map[salesmanId];
    if (!c) return;
    const item = c.items.find((i) => i.product_id === productId);
    if (!item) return;
    const next = Math.max(0, Math.min(Number(item.available || 999), Number(qty)));
    if (next === 0) {
      c.items = c.items.filter((i) => i.product_id !== productId);
    } else {
      item.qty = next;
    }
    c.updated_at = new Date().toISOString();
    map[salesmanId] = c;
    writeMap(map);
  }, [salesmanId]);

  const removeItem = useCallback((productId) => setQty(productId, 0), [setQty]);

  const clear = useCallback(() => {
    if (!salesmanId) return;
    const map = readMap();
    delete map[salesmanId];
    writeMap(map);
  }, [salesmanId]);

  const subtotal = (cart.items || []).reduce(
    (s, i) => s + Number(i.qty || 0) * Number(i.price_usd || 0), 0,
  );
  const units = (cart.items || []).reduce((s, i) => s + Number(i.qty || 0), 0);

  return { cart, items: cart.items || [], units, subtotal, addItem, setQty, removeItem, clear };
}

// Imperative remove — used when clearing a salesman's cart after checkout.
export function clearCartForSalesman(salesmanId) {
  if (!salesmanId) return;
  const map = readMap();
  delete map[salesmanId];
  writeMap(map);
}
