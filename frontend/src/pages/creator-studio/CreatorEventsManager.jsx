import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Loader2, Plus, Ticket, ExternalLink, Calendar, Users, Shield,
  KeyRound, Trash2, ChevronDown, ChevronUp,
} from 'lucide-react';
import { creatorApi } from '../../modules/creator_platform/api.js';
import { useToast } from '../../components/ui/Toast.jsx';

function fmtDate(s) {
  try { return new Date(s).toLocaleString('en-ZW', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Harare' }); }
  catch { return s; }
}

const EMPTY_TICKETED = {
  ticketing_mode: 'host_ticketing', title: '', description: '', venue_name: '',
  event_date: '', end_at: '', category: 'Music',
  ticket_types: [{ name: 'General', price_usd: '10', quantity_total: '100' }],
};
const EMPTY_FREE = {
  ticketing_mode: 'external', title: '', description: '', venue_name: '',
  event_date: '', ticket_price: 'free', external_ticket_url: '',
};

export default function CreatorEventsManager() {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState(null); // 'host_ticketing' | 'external' | null
  const [form, setForm] = useState(EMPTY_TICKETED);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const load = () => creatorApi.listEvents().then((r) => setEvents(r.events)).catch(() => {}).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const openForm = (m) => { setMode(m); setForm(m === 'host_ticketing' ? EMPTY_TICKETED : EMPTY_FREE); };

  const setTT = (i, k, v) => setForm((f) => {
    const tts = [...f.ticket_types]; tts[i] = { ...tts[i], [k]: v }; return { ...f, ticket_types: tts };
  });
  const addTTRow = () => setForm((f) => ({ ...f, ticket_types: [...f.ticket_types, { name: '', price_usd: '0', quantity_total: '50' }] }));

  const create = async () => {
    if (!form.title || !form.event_date) { toast.error('Title and date are required.'); return; }
    setSaving(true);
    try {
      const payload = { ...form };
      if (form.ticketing_mode === 'host_ticketing') {
        payload.ticket_types = form.ticket_types
          .filter((t) => t.name)
          .map((t) => ({ name: t.name, price_usd: t.price_usd, quantity_total: parseInt(t.quantity_total || 0, 10) }));
        if (!payload.ticket_types.length) { toast.error('Add at least one ticket type.'); setSaving(false); return; }
      }
      await creatorApi.createEvent(payload);
      toast.success('Event published.');
      setMode(null);
      load();
    } catch (e) { toast.error(e.message || 'Could not create event'); }
    finally { setSaving(false); }
  };

  const del = async (ce) => {
    if (!window.confirm(`Delete "${ce.title}"? Ticketed events will be cancelled and tickets voided.`)) return;
    try { await creatorApi.deleteEvent(ce.id); toast.success('Removed.'); load(); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="accent-rule font-display text-4xl text-ink">Events</h1>
        <div className="flex gap-2">
          <button className="btn-accent" onClick={() => openForm('host_ticketing')}><Ticket size={15} /> Ticketed</button>
          <button className="btn-secondary" onClick={() => openForm('external')}><ExternalLink size={15} /> Free / external</button>
        </div>
      </div>
      <p className="mt-2 text-sm text-inkm">
        Ticketed events sell through ZimHub's ticketing — same QR tickets and gate scanning as any event. Free / external events just list and link out.
      </p>

      {mode && (
        <div className="mt-5 rounded-xl border border-bordr bg-bgs p-5">
          <h2 className="mb-3 font-display text-xl text-ink">{mode === 'host_ticketing' ? 'New ticketed event' : 'New free / external event'}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <input className="input-base sm:col-span-2" placeholder="Event title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <div>
              <label className="label">Date & time *</label>
              <input type="datetime-local" className="input-base" value={form.event_date} onChange={(e) => setForm({ ...form, event_date: e.target.value })} />
            </div>
            <input className="input-base" placeholder="Venue" value={form.venue_name} onChange={(e) => setForm({ ...form, venue_name: e.target.value })} />
            <textarea className="input-base sm:col-span-2" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>

          {mode === 'host_ticketing' ? (
            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="label !mb-0">Ticket types</span>
                <button className="text-xs text-inkm hover:text-ink" onClick={addTTRow}>+ add type</button>
              </div>
              <div className="space-y-2">
                {form.ticket_types.map((t, i) => (
                  <div key={i} className="grid grid-cols-[1fr,90px,90px] gap-2">
                    <input className="input-base" placeholder="Name" value={t.name} onChange={(e) => setTT(i, 'name', e.target.value)} />
                    <input className="input-base" placeholder="$ price" value={t.price_usd} onChange={(e) => setTT(i, 'price_usd', e.target.value)} />
                    <input className="input-base" placeholder="Qty" value={t.quantity_total} onChange={(e) => setTT(i, 'quantity_total', e.target.value)} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <input className="input-base" placeholder="Price ('free' or e.g. $5)" value={form.ticket_price} onChange={(e) => setForm({ ...form, ticket_price: e.target.value })} />
              <input className="input-base" placeholder="External ticket / RSVP URL" value={form.external_ticket_url} onChange={(e) => setForm({ ...form, external_ticket_url: e.target.value })} />
            </div>
          )}

          <div className="mt-4 flex gap-2">
            <button className="btn-accent" onClick={create} disabled={saving}>{saving ? <Loader2 size={14} className="animate-spin" /> : 'Publish event'}</button>
            <button className="btn-ghost" onClick={() => setMode(null)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {loading ? (
          <div className="flex items-center gap-2 py-10 text-inkm"><Loader2 className="animate-spin" size={16} /> Loading…</div>
        ) : events.length === 0 ? (
          <p className="py-10 text-inkm">No events yet.</p>
        ) : events.map((ce) => (
          <EventRow key={ce.id} ce={ce} expanded={expanded === ce.id} onToggle={() => setExpanded(expanded === ce.id ? null : ce.id)} onDelete={() => del(ce)} reload={load} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ ce, expanded, onToggle, onDelete, reload }) {
  const toast = useToast();
  const ticketed = ce.ticketing_mode === 'host_ticketing' && ce.host_event;
  const [gatemen, setGatemen] = useState([]);
  const [gm, setGm] = useState({ name: '', phone: '' });
  const [tt, setTt] = useState({ name: '', price_usd: '0', quantity_total: '50' });
  const [issuedPin, setIssuedPin] = useState(null);

  useEffect(() => {
    if (expanded && ticketed) creatorApi.listGatemen(ce.id).then((r) => setGatemen(r.gatemen)).catch(() => {});
  }, [expanded]);

  const addGateman = async () => {
    if (!gm.name || !gm.phone) { toast.error('Name and phone required.'); return; }
    try {
      const r = await creatorApi.createGateman(ce.id, gm);
      setIssuedPin({ name: r.gateman.name, pin: r.gateman.pin });
      setGm({ name: '', phone: '' });
      creatorApi.listGatemen(ce.id).then((res) => setGatemen(res.gatemen));
    } catch (e) { toast.error(e.message); }
  };
  const addTicketType = async () => {
    if (!tt.name) { toast.error('Ticket type name required.'); return; }
    try { await creatorApi.addTicketType(ce.id, { ...tt, quantity_total: parseInt(tt.quantity_total || 0, 10) }); toast.success('Ticket type added.'); setTt({ name: '', price_usd: '0', quantity_total: '50' }); reload(); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div className="rounded-xl border border-bordr bg-bgs">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className={`rounded-full px-2 py-0.5 text-[10px] ${ticketed ? 'bg-[rgb(var(--section-accent)/0.16)] text-[rgb(var(--section-accent))]' : 'bg-bgs2 text-inkm'}`}>
          {ticketed ? 'Ticketed' : 'Free / external'}
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-ink">{ce.title}</div>
          <div className="flex items-center gap-1 text-xs text-inkm"><Calendar size={12} /> {fmtDate(ce.event_date)}{ce.venue_name ? ` · ${ce.venue_name}` : ''}</div>
        </div>
        {ticketed && (
          <button onClick={onToggle} className="rounded p-2 text-inkm hover:text-ink">{expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button>
        )}
        <button onClick={onDelete} className="rounded p-2 text-inkm hover:text-danger"><Trash2 size={16} /></button>
      </div>

      {expanded && ticketed && (
        <div className="border-t border-bordr/60 px-4 py-4">
          <div className="mb-4 flex flex-wrap gap-2 text-xs">
            <Link to={`/events/${ce.host_event_id}`} className="inline-flex items-center gap-1 rounded-md border border-bordr px-2 py-1 text-inkm hover:text-ink"><Ticket size={12} /> Public page</Link>
            <Link to="/gate" className="inline-flex items-center gap-1 rounded-md border border-bordr px-2 py-1 text-inkm hover:text-ink"><Shield size={12} /> Open gate scanner</Link>
          </div>

          {/* Ticket types */}
          <div className="mb-4">
            <div className="mb-1 flex items-center gap-1 text-sm text-ink"><Ticket size={14} /> Ticket types</div>
            <div className="space-y-1">
              {(ce.host_event?.ticket_types || []).map((t) => (
                <div key={t.id} className="flex items-center justify-between rounded-md bg-bgs2 px-3 py-1.5 text-xs">
                  <span className="text-ink">{t.name}</span>
                  <span className="text-inkm">${Number(t.price_usd).toFixed(2)} · {t.quantity_sold}/{t.quantity_total} sold</span>
                </div>
              ))}
            </div>
            <div className="mt-2 grid grid-cols-[1fr,80px,80px,auto] gap-2">
              <input className="input-base" placeholder="New type" value={tt.name} onChange={(e) => setTt({ ...tt, name: e.target.value })} />
              <input className="input-base" placeholder="$" value={tt.price_usd} onChange={(e) => setTt({ ...tt, price_usd: e.target.value })} />
              <input className="input-base" placeholder="Qty" value={tt.quantity_total} onChange={(e) => setTt({ ...tt, quantity_total: e.target.value })} />
              <button className="btn-secondary" onClick={addTicketType}><Plus size={14} /></button>
            </div>
          </div>

          {/* Gatemen */}
          <div>
            <div className="mb-1 flex items-center gap-1 text-sm text-ink"><Users size={14} /> Gatemen</div>
            {gatemen.length > 0 && (
              <div className="space-y-1">
                {gatemen.map((g) => (
                  <div key={g.id} className="flex items-center justify-between rounded-md bg-bgs2 px-3 py-1.5 text-xs">
                    <span className="text-ink">{g.name}</span>
                    <span className="text-inkm">{g.phone} · {g.scan_count} scans</span>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-2 grid grid-cols-[1fr,1fr,auto] gap-2">
              <input className="input-base" placeholder="Gateman name" value={gm.name} onChange={(e) => setGm({ ...gm, name: e.target.value })} />
              <input className="input-base" placeholder="Phone" value={gm.phone} onChange={(e) => setGm({ ...gm, phone: e.target.value })} />
              <button className="btn-secondary" onClick={addGateman}><KeyRound size={14} /></button>
            </div>
            {issuedPin && (
              <p className="mt-2 rounded-md bg-[rgb(var(--section-accent)/0.12)] px-3 py-2 text-xs text-ink">
                PIN for <b>{issuedPin.name}</b>: <b className="tabular-nums">{issuedPin.pin}</b> — share it now; it won't be shown again.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
