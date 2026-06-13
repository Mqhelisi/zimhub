import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ArrowLeft, Loader2, Plus, Trash2, ImagePlus } from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import {
  promoterGetEvent,
  promoterCreateTicketedEvent, promoterEditTicketedEvent,
  promoterCreateFlyerEvent, promoterEditFlyerEvent,
  promoterUploadImage,
} from '../../../modules/ticket_generator/api/index.js';

const CATEGORIES = ['Music', 'Church', 'Arts & Culture', 'Festival', 'Sports', 'Comedy', 'Conference', 'Other'];

function toLocalInput(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const off = d.getTimezoneOffset();
    const local = new Date(d.getTime() - off * 60000);
    return local.toISOString().slice(0, 16);
  } catch { return ''; }
}
function fromLocalInput(local) {
  if (!local) return null;
  try { return new Date(local).toISOString(); } catch { return null; }
}

export default function EventEditor() {
  const toast = useToast();
  const { eventId } = useParams();
  const isEdit = !!eventId;
  const navigate = useNavigate();

  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: 'Music',
    start_at: '', end_at: '', location: '',
    poster_url: '', color_scheme: '',
    mode: 'ticketed',
    external_link: '', whatsapp_deep_link_text: '',
    ticket_types: [{ name: 'General', price_usd: '5.00', quantity_total: 100 }],
    status: 'draft',
  });

  useEffect(() => {
    if (!isEdit) return;
    setLoading(true);
    promoterGetEvent(eventId).then((r) => {
      const e = r.event;
      setForm({
        title: e.title || '', description: e.description || '',
        category: e.category || 'Other',
        start_at: toLocalInput(e.start_at), end_at: toLocalInput(e.end_at),
        location: e.location || '',
        poster_url: e.poster_url || '',
        color_scheme: e.color_scheme || '',
        mode: e.mode || 'ticketed',
        external_link: e.external_link || '',
        whatsapp_deep_link_text: e.whatsapp_deep_link_text || '',
        ticket_types: (e.ticket_types || []).map((t) => ({
          id: t.id, name: t.name,
          price_usd: String(t.price_usd),
          quantity_total: t.quantity_total,
          quantity_sold: t.quantity_sold,
        })),
        status: e.status,
      });
    }).catch((err) => {
      toast.error(err.message || 'Could not load event');
    }).finally(() => setLoading(false));
  }, [eventId, isEdit]);

  function update(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function onUploadPoster(file) {
    if (!file) return;
    try {
      toast.info('Uploading…');
      const url = await promoterUploadImage(file);
      update('poster_url', url);
      toast.success('Poster uploaded');
    } catch (e) {
      toast.error(e.message || 'Upload failed');
    }
  }

  async function onSave(action = 'save') {
    setSaving(true);
    try {
      const base = {
        title: form.title, description: form.description,
        category: form.category, location: form.location,
        poster_url: form.poster_url || null,
        color_scheme: form.color_scheme || null,
        start_at: fromLocalInput(form.start_at),
        end_at: fromLocalInput(form.end_at),
      };
      let result;
      if (isEdit) {
        if (form.mode === 'flyer') {
          result = await promoterEditFlyerEvent(eventId, {
            ...base,
            external_link: form.external_link || null,
            whatsapp_deep_link_text: form.whatsapp_deep_link_text || null,
          });
        } else {
          result = await promoterEditTicketedEvent(eventId, base);
        }
        toast.success('Saved.');
        navigate(`/promoter/events/${result.event.id}`);
      } else {
        if (form.mode === 'flyer') {
          result = await promoterCreateFlyerEvent({
            ...base,
            external_link: form.external_link || null,
            whatsapp_deep_link_text: form.whatsapp_deep_link_text || null,
          });
        } else {
          result = await promoterCreateTicketedEvent({
            ...base, status: action === 'publish' ? 'active' : 'draft',
            ticket_types: form.ticket_types.map((t) => ({
              name: t.name, price_usd: t.price_usd,
              quantity_total: Number(t.quantity_total) || 0,
            })),
          });
        }
        toast.success('Event created.');
        navigate(`/promoter/events/${result.event.id}`);
      }
    } catch (e) {
      const fe = e?.payload?.error?.field_errors;
      if (fe) {
        const first = Object.entries(fe)[0];
        toast.error(`${first[0]}: ${first[1]}`);
      } else {
        toast.error(e.message || 'Save failed');
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
        <Loader2 className="animate-spin" size={16} /> Loading…
      </div>
    );
  }

  return (
    <main className="container-page py-8 max-w-3xl space-y-5">
      <Link to="/promoter/events" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> My events
      </Link>
      <h1 className="font-display text-3xl text-ink heading-accent">
        {isEdit ? 'Edit event' : 'New event'}
      </h1>

      <div className="card p-4">
        <div className="label">Event format</div>
        <div className="flex gap-2">
          {[
            { v: 'ticketed', label: 'Ticketed', desc: 'Sell tickets on ZimHub with QR check-in.' },
            { v: 'flyer', label: 'Flyer', desc: 'Just a poster — RSVP/buy off-platform.' },
          ].map((opt) => (
            <button key={opt.v} type="button"
              disabled={isEdit && form.mode !== opt.v && form.mode === 'ticketed'}
              onClick={() => !isEdit && update('mode', opt.v)}
              className={`flex-1 rounded-lg border px-3 py-2.5 text-left transition ${
                form.mode === opt.v ? 'border-brand bg-bgs2' : 'border-bordr bg-bgs hover:border-brand/40'
              } ${isEdit && form.mode !== opt.v ? 'opacity-50 cursor-not-allowed' : ''}`}>
              <div className="text-ink font-medium">{opt.label}</div>
              <div className="text-xs text-inkm">{opt.desc}</div>
            </button>
          ))}
        </div>
        {isEdit && form.mode === 'flyer' && (
          <p className="text-xs text-inkm mt-3">
            You can convert this flyer to ticketed from the event manage page (one-way).
          </p>
        )}
      </div>

      <div className="card p-5 space-y-4">
        <div>
          <label className="label">Title</label>
          <input className="input-base" value={form.title}
                 onChange={(e) => update('title', e.target.value)} />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea rows={4} className="input-base"
            value={form.description} onChange={(e) => update('description', e.target.value)} />
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="label">Category</label>
            <select className="input-base" value={form.category}
                    onChange={(e) => update('category', e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Location</label>
            <input className="input-base" value={form.location}
                   onChange={(e) => update('location', e.target.value)} />
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="label">Start</label>
            <input type="datetime-local" className="input-base" value={form.start_at}
                   onChange={(e) => update('start_at', e.target.value)} />
          </div>
          <div>
            <label className="label">End</label>
            <input type="datetime-local" className="input-base" value={form.end_at}
                   onChange={(e) => update('end_at', e.target.value)} />
          </div>
        </div>
        <div>
          <label className="label">Poster</label>
          {form.poster_url ? (
            <div className="flex items-center gap-3">
              <img src={form.poster_url} className="h-24 w-24 object-cover rounded-md" />
              <button type="button" onClick={() => update('poster_url', '')}
                      className="btn-secondary"><Trash2 size={14} /> Remove</button>
            </div>
          ) : (
            <label className="inline-flex items-center gap-2 cursor-pointer btn-secondary">
              <ImagePlus size={14} /> Upload poster
              <input type="file" accept="image/*" className="hidden"
                     onChange={(e) => onUploadPoster(e.target.files?.[0])} />
            </label>
          )}
        </div>
      </div>

      {form.mode === 'flyer' ? (
        <div className="card p-5 space-y-4">
          <h2 className="font-display text-lg text-ink">Flyer details</h2>
          <div>
            <label className="label">External link (optional)</label>
            <input className="input-base"
                   placeholder="https://example.com/event-rsvp"
                   value={form.external_link}
                   onChange={(e) => update('external_link', e.target.value)} />
          </div>
          <div>
            <label className="label">WhatsApp greeting (optional)</label>
            <textarea className="input-base" rows={3}
              placeholder="Hi, I want to RSVP for your event…"
              value={form.whatsapp_deep_link_text}
              onChange={(e) => update('whatsapp_deep_link_text', e.target.value)} />
            <p className="text-[11px] text-inkm mt-1">
              Pre-fills the WhatsApp message buyers send to your phone.
            </p>
          </div>
        </div>
      ) : (
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg text-ink">Ticket types</h2>
            {!isEdit && (
              <button type="button" className="btn-secondary"
                onClick={() => setForm((f) => ({
                  ...f, ticket_types: [...f.ticket_types,
                    { name: '', price_usd: '0.00', quantity_total: 0 }],
                }))}><Plus size={14} /> Add type</button>
            )}
          </div>
          {isEdit && (
            <p className="text-xs text-inkm">
              Edit individual types from the event manage page. This editor only sets ticket types when creating.
            </p>
          )}
          {!isEdit && form.ticket_types.map((t, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-2 items-end border border-bordr rounded-lg p-3">
              <div className="col-span-6">
                <label className="label">Name</label>
                <input className="input-base" value={t.name}
                       onChange={(e) => setForm((f) => {
                         const next = [...f.ticket_types];
                         next[idx] = { ...next[idx], name: e.target.value };
                         return { ...f, ticket_types: next };
                       })} />
              </div>
              <div className="col-span-3">
                <label className="label">Price (USD)</label>
                <input className="input-base" type="number" step="0.01" min="0" value={t.price_usd}
                       onChange={(e) => setForm((f) => {
                         const next = [...f.ticket_types];
                         next[idx] = { ...next[idx], price_usd: e.target.value };
                         return { ...f, ticket_types: next };
                       })} />
              </div>
              <div className="col-span-2">
                <label className="label">Quantity</label>
                <input className="input-base" type="number" min="0" value={t.quantity_total}
                       onChange={(e) => setForm((f) => {
                         const next = [...f.ticket_types];
                         next[idx] = { ...next[idx], quantity_total: e.target.value };
                         return { ...f, ticket_types: next };
                       })} />
              </div>
              <div className="col-span-1 flex justify-end">
                <button type="button" className="btn-ghost text-danger"
                  onClick={() => setForm((f) => ({
                    ...f, ticket_types: f.ticket_types.filter((_, i) => i !== idx),
                  }))}><Trash2 size={14} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 justify-end">
        <Link to="/promoter/events" className="btn-secondary">Cancel</Link>
        {!isEdit && form.mode === 'ticketed' && (
          <button type="button" className="btn-secondary" disabled={saving} onClick={() => onSave('save')}>
            Save as draft
          </button>
        )}
        <button type="button" className="btn-primary" disabled={saving} onClick={() => onSave('publish')}>
          {saving ? <><Loader2 size={14} className="animate-spin" /> Saving…</> :
            (isEdit ? 'Save' : (form.mode === 'flyer' ? 'Publish flyer' : 'Save & publish'))}
        </button>
      </div>
    </main>
  );
}
