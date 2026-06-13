import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Calendar, MapPin, User, Minus, Plus, Loader2, ArrowLeft, ExternalLink, MessageCircle } from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import { getEvent } from '../../../modules/ticket_generator/api/index.js';
import { purchaseInterfaceApi } from '../../../modules/purchase_interface/api.js';
import { useAuth } from '../../../contexts/AuthContext.jsx';

function fmtDateRange(start, end) {
  const opts = { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare' };
  try {
    const s = new Date(start), e = new Date(end);
    return `${s.toLocaleString('en-ZW', opts)} — ${e.toLocaleString('en-ZW', { hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare' })}`;
  } catch { return start; }
}

export default function EventDetailPage() {
  const toast = useToast();
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedTypeId, setSelectedTypeId] = useState(null);
  const [qty, setQty] = useState(1);
  const [attendees, setAttendees] = useState(['']);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setLoading(true);
    getEvent(id)
      .then((r) => {
        setEvent(r.event);
        const firstType = (r.event.ticket_types || []).find((t) => t.quantity_remaining > 0)
                       || (r.event.ticket_types || [])[0];
        if (firstType) setSelectedTypeId(firstType.id);
      })
      .catch((e) => toast.error(e.message || 'Could not load event'))
      .finally(() => setLoading(false));
  }, [id]);

  const selectedType = useMemo(() => {
    return (event?.ticket_types || []).find((t) => t.id === selectedTypeId);
  }, [event, selectedTypeId]);

  // Keep attendee-names array length in sync with qty.
  useEffect(() => {
    setAttendees((prev) => {
      const next = [...prev];
      while (next.length < qty) next.push('');
      while (next.length > qty) next.pop();
      return next;
    });
  }, [qty]);

  // Reset qty when type changes (avoid over-asking).
  useEffect(() => { setQty(1); }, [selectedTypeId]);

  async function buyTickets() {
    if (!user) {
      toast.error('Please log in to buy tickets.');
      navigate('/login', { state: { next: `/events/${id}` } });
      return;
    }
    if (!selectedType) return;
    const cleaned = attendees.map((n) => n.trim()).filter(Boolean);
    if (cleaned.length !== qty) {
      toast.error(`Please enter all ${qty} attendee names.`);
      return;
    }
    setSubmitting(true);
    try {
      const purchase = await purchaseInterfaceApi.initiate({
        listing_type: 'event_ticket',
        listing_id: selectedType.id,
        quantity: qty,
        domain_payload: {
          attendee_names: cleaned,
          buyer_name_at_purchase: user.name,
          buyer_phone_at_purchase: user.phone,
        },
      });
      toast.success('Tickets reserved. Coordinate payment on WhatsApp.');
      navigate(`/events/${id}/checkout/${purchase.id}/success`);
    } catch (e) {
      const msg = e?.payload?.error?.message || e?.response?.data?.message || e.message || 'Could not buy tickets.';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  function whatsappRsvpUrl() {
    if (!event) return '#';
    const text = event.whatsapp_deep_link_text
      || `Hi, I'm interested in your event: ${event.title}. Is it still on?`;
    const phone = event.promoter?.phone?.replace(/[^+\d]/g, '') || '';
    return `https://wa.me/${phone.replace(/^\+/, '')}?text=${encodeURIComponent(text)}`;
  }

  if (loading) {
    return <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
      <Loader2 className="animate-spin" size={16} /> Loading event…
    </div>;
  }
  if (!event) {
    return <div className="container-page py-16 text-inkm">Event not found.</div>;
  }
  const poster = event.poster_url || event.poster_thumb_url;
  const isCancelled = event.status === 'cancelled';

  return (
    <main className="container-page py-8">
      <Link to="/events" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1 mb-3">
        <ArrowLeft size={14} /> Back to events
      </Link>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-5">
          <div className="event-poster-frame">
            {poster ? (
              <img src={poster} alt={event.title} className="w-full max-h-[480px] object-cover" />
            ) : (
              <div className="aspect-video bg-bgs2" />
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`pill ${event.mode === 'flyer' ? 'mode-pill-flyer' : 'mode-pill-ticketed'}`}>
              {event.mode === 'flyer' ? 'Flyer' : 'Ticketed'}
            </span>
            <span className="pill">{event.category}</span>
            {isCancelled && <span className="pill mode-pill-cancelled">Cancelled</span>}
          </div>
          <h1 className="font-display text-3xl sm:text-4xl text-ink heading-accent">{event.title}</h1>
          <div className="text-sm text-inkm space-y-1">
            <div className="flex items-center gap-2"><Calendar size={14} /> {fmtDateRange(event.start_at, event.end_at)}</div>
            {event.location && <div className="flex items-center gap-2"><MapPin size={14} /> {event.location}</div>}
            {event.promoter && (
              <div className="flex items-center gap-2">
                <User size={14} /> {event.promoter.organisation_name || event.promoter.name}
              </div>
            )}
          </div>
          {event.description && (
            <p className="text-ink whitespace-pre-line leading-relaxed">{event.description}</p>
          )}
        </div>

        <aside className="space-y-5">
          {event.mode === 'flyer' ? (
            <div className="card p-5 space-y-4">
              <h2 className="font-display text-lg text-ink">RSVP / Details</h2>
              <p className="text-sm text-inkm">
                This event is hosted off-platform. Tap below to follow the link or message the promoter on WhatsApp.
              </p>
              {event.external_link && (
                <a href={event.external_link} target="_blank" rel="noreferrer noopener"
                   className="btn-primary w-full">
                  <ExternalLink size={16} /> Open event link
                </a>
              )}
              {event.promoter?.phone && (
                <a href={whatsappRsvpUrl()} target="_blank" rel="noreferrer noopener"
                   className="btn-secondary w-full">
                  <MessageCircle size={16} /> Message promoter on WhatsApp
                </a>
              )}
            </div>
          ) : (
            <div className="card p-5 space-y-4">
              <h2 className="font-display text-lg text-ink">Choose tickets</h2>
              {isCancelled ? (
                <p className="text-sm text-danger">This event is cancelled. No tickets available.</p>
              ) : (event.ticket_types || []).length === 0 ? (
                <p className="text-sm text-inkm">No ticket types published yet.</p>
              ) : (
                <>
                  <div className="space-y-2">
                    {(event.ticket_types || []).map((t) => {
                      const remaining = t.quantity_remaining;
                      const isSelected = selectedTypeId === t.id;
                      const soldOut = remaining <= 0;
                      return (
                        <button key={t.id} type="button"
                          disabled={soldOut}
                          onClick={() => !soldOut && setSelectedTypeId(t.id)}
                          className={`w-full text-left rounded-lg border px-3 py-2.5 transition ${
                            isSelected ? 'border-brand bg-bgs2' : 'border-bordr bg-bgs hover:border-brand/50'
                          } ${soldOut ? 'opacity-60 cursor-not-allowed' : ''}`}>
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-ink font-medium">{t.name}</span>
                            <span className="text-ink font-semibold">${Number(t.price_usd).toFixed(2)}</span>
                          </div>
                          {t.description && <div className="text-xs text-inkm mt-1">{t.description}</div>}
                          <div className="text-[11px] text-inkm mt-1">
                            {soldOut ? 'Sold out' : `${remaining} left`}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {selectedType && selectedType.quantity_remaining > 0 && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-inkm">Quantity</span>
                        <div className="inline-flex items-center gap-2">
                          <button type="button" onClick={() => setQty((q) => Math.max(1, q - 1))}
                            className="h-8 w-8 rounded-md border border-bordr bg-bgs2 inline-flex items-center justify-center text-inkm hover:text-ink">
                            <Minus size={14} />
                          </button>
                          <span className="w-8 text-center text-ink font-semibold">{qty}</span>
                          <button type="button"
                            onClick={() => setQty((q) => Math.min(selectedType.quantity_remaining, q + 1))}
                            className="h-8 w-8 rounded-md border border-bordr bg-bgs2 inline-flex items-center justify-center text-inkm hover:text-ink">
                            <Plus size={14} />
                          </button>
                        </div>
                      </div>

                      <div className="space-y-2 pt-2">
                        <div className="label">Attendee names</div>
                        {Array.from({ length: qty }).map((_, i) => (
                          <input key={i} className="input-base"
                            placeholder={`Attendee ${i + 1} name`}
                            value={attendees[i] || ''}
                            onChange={(e) => setAttendees((arr) => {
                              const next = [...arr];
                              next[i] = e.target.value;
                              return next;
                            })} />
                        ))}
                      </div>

                      <div className="flex items-center justify-between border-t border-bordr pt-3">
                        <span className="text-sm text-inkm">Total</span>
                        <span className="text-ink font-display text-xl">
                          ${(Number(selectedType.price_usd) * qty).toFixed(2)}
                        </span>
                      </div>

                      <button type="button" className="btn-primary w-full"
                              disabled={submitting} onClick={buyTickets}>
                        {submitting ? <><Loader2 size={14} className="animate-spin" /> Reserving…</> : 'Buy tickets'}
                      </button>
                      <p className="text-[11px] text-inkm">
                        You'll coordinate payment over WhatsApp after committing.
                      </p>
                    </>
                  )}
                </>
              )}
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
