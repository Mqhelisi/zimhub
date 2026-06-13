import React, { useEffect, useState } from 'react';
import { Loader2, Ticket as TicketIcon } from 'lucide-react';
import { TicketCard } from '../../modules/ticket_generator/components/TicketCard.jsx';
import { listMyTickets } from '../../modules/ticket_generator/api/index.js';

export default function BuyerTicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listMyTickets()
      .then((r) => setTickets(r.tickets || []))
      .finally(() => setLoading(false));
  }, []);

  const valid = tickets.filter((t) => t.status === 'valid');
  const past = tickets.filter((t) => t.status !== 'valid');

  return (
    <main className="container-page py-8 space-y-6">
      <h1 className="font-display text-3xl text-ink heading-accent inline-flex items-center gap-3">
        <TicketIcon size={28} className="text-brand" /> My tickets
      </h1>
      {loading ? (
        <div className="text-inkm flex items-center gap-2 py-12 justify-center">
          <Loader2 className="animate-spin" size={16} /> Loading…
        </div>
      ) : tickets.length === 0 ? (
        <div className="card p-8 text-center text-inkm">
          You don't have any tickets yet. Browse <a href="/events">events</a> to grab some.
        </div>
      ) : (
        <>
          {valid.length > 0 && (
            <section className="space-y-3">
              <h2 className="font-display text-lg text-ink">Valid</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                {valid.map((t) => <TicketCard key={t.id} ticket={t} />)}
              </div>
            </section>
          )}
          {past.length > 0 && (
            <section className="space-y-3">
              <h2 className="font-display text-lg text-inkm">Used / voided</h2>
              <div className="grid gap-3 sm:grid-cols-2 opacity-80">
                {past.map((t) => <TicketCard key={t.id} ticket={t} />)}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}
