import React from 'react';
import { Ticket, Megaphone, Ban } from 'lucide-react';

export function ModePill({ event, className = '' }) {
  if (!event) return null;
  const isCancelled = event.status === 'cancelled';
  if (isCancelled) {
    return (
      <span className={`pill mode-pill-cancelled ${className}`}>
        <Ban size={12} /> Cancelled
      </span>
    );
  }
  if (event.mode === 'flyer') {
    return (
      <span className={`pill mode-pill-flyer ${className}`}>
        <Megaphone size={12} /> Flyer
      </span>
    );
  }
  // ticketed — show the cheapest type if we have ticket_types
  const types = event.ticket_types || [];
  const prices = types.map((t) => parseFloat(t.price_usd || 0)).filter((p) => !isNaN(p));
  const min = prices.length ? Math.min(...prices) : null;
  return (
    <span className={`pill mode-pill-ticketed ${className}`}>
      <Ticket size={12} /> {min != null ? `Tickets from $${min.toFixed(2)}` : 'Tickets'}
    </span>
  );
}

export default ModePill;
