import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, ArrowLeft, Send, Calendar, MapPin } from 'lucide-react';
import { useToast } from '../../components/ui/Toast.jsx';
import { getTicket, resendTicket } from '../../modules/ticket_generator/api/index.js';
import { QRCodeView } from '../../modules/ticket_generator/components/QRCodeView.jsx';

export default function BuyerTicketDetailPage() {
  const toast = useToast();
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    setLoading(true);
    getTicket(ticketId)
      .then((r) => setTicket(r.ticket))
      .catch((e) => toast.error(e.message || 'Could not load ticket'))
      .finally(() => setLoading(false));
  }, [ticketId]);

  async function onResend() {
    setSending(true);
    try {
      await resendTicket(ticketId);
      toast.success('Resent over SMS and WhatsApp.');
    } catch (e) {
      toast.error(e.message || 'Could not resend');
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
      <Loader2 className="animate-spin" size={16} /> Loading ticket…
    </div>;
  }
  if (!ticket) return <div className="container-page py-16 text-inkm">Ticket not found.</div>;

  const ev = ticket.event || {};
  const tt = ticket.ticket_type || {};
  const isValid = ticket.status === 'valid';

  return (
    <main className="container-page py-8">
      <Link to="/my/tickets" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1 mb-3">
        <ArrowLeft size={14} /> My tickets
      </Link>

      <div className="grid gap-6 lg:grid-cols-2 mt-4">
        <div className="card p-6 flex flex-col items-center justify-center bg-bgs">
          {isValid ? (
            <>
              <QRCodeView value={ticket.qr_code} size={260}
                          label={`#${ticket.id.slice(0, 8).toUpperCase()}`} />
              <p className="mt-4 text-xs text-inkm text-center max-w-[260px]">
                Show this QR at the gate. Brightness all the way up.
              </p>
            </>
          ) : ticket.status === 'used' ? (
            <div className="text-center text-inkm">
              <div className="text-4xl font-display text-ink mb-2">Used</div>
              <div>Scanned {ticket.checked_in_at ? new Date(ticket.checked_in_at).toLocaleString('en-ZW') : ''}</div>
            </div>
          ) : (
            <div className="text-center text-danger">
              <div className="text-4xl font-display mb-2">Voided</div>
              <div className="text-inkm text-sm">Open the purchase for details.</div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h1 className="font-display text-3xl text-ink heading-accent">{ev.title || 'Event'}</h1>
          <div className="text-sm text-inkm space-y-1">
            {ev.start_at && (
              <div className="flex items-center gap-2"><Calendar size={14} />
                {new Date(ev.start_at).toLocaleString('en-ZW', { timeZone: 'Africa/Harare' })}
              </div>
            )}
            {ev.location && <div className="flex items-center gap-2"><MapPin size={14} /> {ev.location}</div>}
          </div>
          <div className="card p-4 space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-inkm">Ticket type</span><span className="text-ink">{tt.name || '—'}</span></div>
            <div className="flex justify-between"><span className="text-inkm">Attendee</span><span className="text-ink">{ticket.attendee_name}</span></div>
            <div className="flex justify-between"><span className="text-inkm">Price</span><span className="text-ink">${ticket.price_usd}</span></div>
            <div className="flex justify-between"><span className="text-inkm">Status</span><span className="text-ink capitalize">{ticket.status}</span></div>
          </div>
          {isValid && (
            <button onClick={onResend} disabled={sending} className="btn-secondary w-full">
              {sending ? <><Loader2 size={14} className="animate-spin" /> Sending…</> : <><Send size={14} /> Resend QR over SMS + WhatsApp</>}
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
