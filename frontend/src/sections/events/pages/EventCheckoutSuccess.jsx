import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle2, MessageCircle, Ticket } from 'lucide-react';
import { purchaseInterfaceApi } from '../../../modules/purchase_interface/api.js';

export default function EventCheckoutSuccess() {
  const { purchaseId } = useParams();
  const [purchase, setPurchase] = useState(null);

  useEffect(() => {
    purchaseInterfaceApi.get(purchaseId).then(setPurchase).catch(() => {});
  }, [purchaseId]);

  return (
    <main className="container-page py-12">
      <div className="card text-center max-w-xl mx-auto p-8">
        <CheckCircle2 size={42} className="mx-auto text-success" />
        <h1 className="mt-3 font-display text-3xl text-ink">Tickets reserved</h1>
        <p className="mt-2 text-inkm">
          The promoter has been notified. Coordinate payment over WhatsApp.
          Your tickets become scannable the moment the promoter confirms payment.
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
          <Link to="/my/tickets" className="btn-secondary">
            <Ticket size={14} /> My tickets
          </Link>
        </div>
      </div>
    </main>
  );
}
