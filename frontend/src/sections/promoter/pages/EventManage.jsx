import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Loader2, Edit3, Users, Download, Plus, Trash2,
  Megaphone, Ticket, AlertTriangle, ShieldCheck, RefreshCw,
} from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import {
  promoterGetEvent, promoterPublishEvent, promoterCancelEvent,
  promoterAttendees, promoterAttendeesCsvUrl,
  promoterAddTicketType, promoterEditTicketType, promoterDeleteTicketType,
  promoterConvertToTicketed,
} from '../../../modules/ticket_generator/api/index.js';
import { ModePill } from '../../events/components/ModePill.jsx';

function StatusBadge({ status }) {
  const map = {
    draft: 'bg-bgs2 text-inkm border-bordr',
    pending_approval: 'bg-warning/10 text-warning border-warning/40',
    active: 'bg-success/15 text-success border-success/40',
    rejected: 'bg-danger/10 text-danger border-danger/40',
    cancelled: 'bg-danger/15 text-danger border-danger/40',
    archived: 'bg-bgs2 text-inkm border-bordr',
  };
  const cls = map[status] || map.draft;
  return <span className={`pill ${cls}`}>{status}</span>;
}

export default function EventManage() {
  const toast = useToast();
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState({ attendees: [], summary: {} });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  // Ticket type editor (inline)
  const [newType, setNewType] = useState({ name: '', price_usd: '0.00', quantity_total: 0 });

  async function reload() {
    setLoading(true);
    try {
      const r = await promoterGetEvent(eventId);
      setEvent(r.event);
      if (r.event.mode === 'ticketed') {
        const a = await promoterAttendees(eventId);
        setAttendees(a);
      }
    } catch (e) {
      toast.error(e.message || 'Could not load event');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, [eventId]);

  async function onPublish() {
    setBusy(true);
    try {
      await promoterPublishEvent(eventId);
      toast.success('Published.');
      await reload();
    } catch (e) { toast.error(e.message || 'Publish failed'); }
    finally { setBusy(false); }
  }

  async function onCancel() {
    if (!confirm('Cancel this event? All valid tickets will be voided and buyers notified.')) return;
    setBusy(true);
    try {
      const r = await promoterCancelEvent(eventId);
      toast.success(`Event cancelled. ${r.voided_tickets} ticket(s) voided.`);
      await reload();
    } catch (e) { toast.error(e.message || 'Cancel failed'); }
    finally { setBusy(false); }
  }

  async function onAddType(e) {
    e?.preventDefault?.();
    if (!newType.name.trim()) return toast.error('Type name required');
    setBusy(true);
    try {
      await promoterAddTicketType(eventId, {
        name: newType.name, price_usd: newType.price_usd,
        quantity_total: Number(newType.quantity_total) || 0,
      });
      setNewType({ name: '', price_usd: '0.00', quantity_total: 0 });
      toast.success('Ticket type added.');
      await reload();
    } catch (e) { toast.error(e.message || 'Failed'); }
    finally { setBusy(false); }
  }

  async function onDeleteType(ttId) {
    if (!confirm('Delete this ticket type? (Only allowed if 0 sold and 0 held.)')) return;
    setBusy(true);
    try {
      await promoterDeleteTicketType(ttId);
      toast.success('Deleted.');
      await reload();
    } catch (e) { toast.error(e.message || 'Could not delete (tickets exist)'); }
    finally { setBusy(false); }
  }

  async function onConvertToTicketed() {
    if (!confirm('Convert this flyer to a ticketed event? This is one-way.')) return;
    setBusy(true);
    try {
      await promoterConvertToTicketed(eventId, {
        ticket_types: [{ name: 'General', price_usd: '5.00', quantity_total: 100 }],
      });
      toast.success('Converted to ticketed.');
      navigate(`/promoter/events/${eventId}/edit`);
    } catch (e) { toast.error(e.message || 'Convert failed'); }
    finally { setBusy(false); }
  }

  if (loading) {
    return <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
      <Loader2 className="animate-spin" size={16} /> Loading…
    </div>;
  }
  if (!event) return <div className="container-page py-16 text-inkm">Event not found.</div>;

  return (
    <main className="container-page py-8 space-y-6">
      <Link to="/promoter/events" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> My events
      </Link>

      <header className="flex items-start justify-between gap-3 flex-wrap">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <ModePill event={event} />
            <StatusBadge status={event.status} />
          </div>
          <h1 className="font-display text-3xl text-ink heading-accent">{event.title}</h1>
          <p className="text-inkm text-sm">{event.location} • {new Date(event.start_at).toLocaleString('en-ZW')}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to={`/promoter/events/${eventId}/edit`} className="btn-secondary">
            <Edit3 size={14} /> Edit
          </Link>
          {event.status === 'draft' && (
            <button onClick={onPublish} disabled={busy} className="btn-primary">
              <ShieldCheck size={14} /> Publish
            </button>
          )}
          {event.status !== 'cancelled' && (
            <button onClick={onCancel} disabled={busy} className="btn-danger">
              <AlertTriangle size={14} /> Cancel event
            </button>
          )}
        </div>
      </header>

      {event.mode === 'flyer' ? (
        <section className="card p-5 space-y-3">
          <h2 className="font-display text-lg text-ink flex items-center gap-2">
            <Megaphone size={18} /> Flyer details
          </h2>
          <div className="text-sm grid sm:grid-cols-2 gap-3">
            <div><div className="label">External link</div>
              {event.external_link
                ? <a className="text-brand" href={event.external_link} target="_blank" rel="noreferrer">{event.external_link}</a>
                : <span className="text-inkm">—</span>}
            </div>
            <div><div className="label">WhatsApp greeting</div>
              <div className="text-ink">{event.whatsapp_deep_link_text || <span className="text-inkm">—</span>}</div>
            </div>
          </div>
          <div className="pt-2">
            <button onClick={onConvertToTicketed} className="btn-secondary" disabled={busy}>
              <RefreshCw size={14} /> Convert to ticketed event
            </button>
          </div>
        </section>
      ) : (
        <>
          {/* Summary */}
          <section className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {[
              ['Total tickets', attendees.summary.total ?? 0],
              ['Checked in', attendees.summary.checked_in ?? 0],
              ['Online', attendees.summary.online ?? 0],
              ['Walk-in', attendees.summary.walk_in ?? 0],
              ['Voided', attendees.summary.voided ?? 0],
            ].map(([label, val]) => (
              <div key={label} className="card p-3 text-center">
                <div className="text-2xl font-display text-ink">{val}</div>
                <div className="text-[11px] uppercase tracking-wider text-inkm">{label}</div>
              </div>
            ))}
          </section>

          {/* Ticket types */}
          <section className="card p-5 space-y-4">
            <h2 className="font-display text-lg text-ink flex items-center gap-2">
              <Ticket size={18} /> Ticket types
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-inkm text-xs uppercase tracking-wider">
                  <tr>
                    <th className="pb-2 pr-2">Name</th>
                    <th className="pb-2 pr-2">Price</th>
                    <th className="pb-2 pr-2">Sold</th>
                    <th className="pb-2 pr-2">Held</th>
                    <th className="pb-2 pr-2">Remaining</th>
                    <th className="pb-2 pr-2">Total</th>
                    <th className="pb-2 pr-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {(event.ticket_types || []).map((t) => (
                    <tr key={t.id} className="border-t border-bordr/60">
                      <td className="py-2 pr-2 text-ink">{t.name}</td>
                      <td className="py-2 pr-2">${t.price_usd}</td>
                      <td className="py-2 pr-2">{t.quantity_sold}</td>
                      <td className="py-2 pr-2">{t.quantity_held}</td>
                      <td className="py-2 pr-2">{t.quantity_remaining}</td>
                      <td className="py-2 pr-2">{t.quantity_total}</td>
                      <td className="py-2 pr-2 text-right">
                        {t.quantity_sold === 0 && t.quantity_held === 0 && (
                          <button onClick={() => onDeleteType(t.id)} className="btn-ghost text-danger">
                            <Trash2 size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <form onSubmit={onAddType} className="grid grid-cols-12 gap-2 items-end border-t border-bordr/40 pt-3">
              <div className="col-span-5">
                <label className="label">Add new type</label>
                <input className="input-base" placeholder="Name (e.g. VIP)"
                       value={newType.name}
                       onChange={(e) => setNewType((n) => ({ ...n, name: e.target.value }))} />
              </div>
              <div className="col-span-3">
                <label className="label">Price USD</label>
                <input className="input-base" type="number" step="0.01" min="0"
                       value={newType.price_usd}
                       onChange={(e) => setNewType((n) => ({ ...n, price_usd: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <label className="label">Qty</label>
                <input className="input-base" type="number" min="0"
                       value={newType.quantity_total}
                       onChange={(e) => setNewType((n) => ({ ...n, quantity_total: e.target.value }))} />
              </div>
              <div className="col-span-2">
                <button type="submit" disabled={busy} className="btn-primary w-full">
                  <Plus size={14} /> Add
                </button>
              </div>
            </form>
          </section>

          {/* Attendees */}
          <section className="card p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <h2 className="font-display text-lg text-ink flex items-center gap-2">
                <Users size={18} /> Attendees
              </h2>
              <div className="flex gap-2">
                <a href={promoterAttendeesCsvUrl(eventId, 'all')} className="btn-secondary">
                  <Download size={14} /> Full CSV
                </a>
                <a href={promoterAttendeesCsvUrl(eventId, 'checked_in')} className="btn-secondary">
                  <Download size={14} /> Checked-in CSV
                </a>
              </div>
            </div>
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-sm">
                <thead className="text-left text-inkm text-xs uppercase tracking-wider sticky top-0 bg-bgs">
                  <tr>
                    <th className="pb-2 pr-2">#</th>
                    <th className="pb-2 pr-2">Attendee</th>
                    <th className="pb-2 pr-2">Type</th>
                    <th className="pb-2 pr-2">Source</th>
                    <th className="pb-2 pr-2">Status</th>
                    <th className="pb-2 pr-2">Checked in</th>
                    <th className="pb-2 pr-2">Gateman</th>
                  </tr>
                </thead>
                <tbody>
                  {(attendees.attendees || []).map((a) => (
                    <tr key={a.id} className="border-t border-bordr/60">
                      <td className="py-2 pr-2 text-inkm">{a.short_id}</td>
                      <td className="py-2 pr-2 text-ink">{a.attendee_name}</td>
                      <td className="py-2 pr-2">{a.ticket_type}</td>
                      <td className="py-2 pr-2 capitalize">{a.source}</td>
                      <td className="py-2 pr-2 capitalize">{a.status}</td>
                      <td className="py-2 pr-2">{a.checked_in_at ? new Date(a.checked_in_at).toLocaleString('en-ZW', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'}</td>
                      <td className="py-2 pr-2">{a.gateman_name || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(attendees.attendees || []).length === 0 && (
                <div className="text-center text-inkm py-6">No attendees yet.</div>
              )}
            </div>
          </section>

          {/* Gatemen link */}
          <section className="card p-5 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h2 className="font-display text-lg text-ink">Gatemen</h2>
              <p className="text-inkm text-sm">Manage scanner phones + PINs for this event.</p>
            </div>
            <Link to={`/promoter/events/${eventId}/gatemen`} className="btn-primary">
              <Users size={14} /> Manage gatemen
            </Link>
          </section>
        </>
      )}
    </main>
  );
}
