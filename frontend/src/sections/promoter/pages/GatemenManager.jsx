import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Loader2, Plus, KeyRound, Trash2, MessageCircle, ShieldCheck } from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import {
  promoterListGatemen, promoterCreateGateman,
  promoterRegenerateGatemanPin, promoterRevokeGateman,
  promoterGetEvent,
} from '../../../modules/ticket_generator/api/index.js';

function pinShareMessage({ event, gateman, pin }) {
  const url = `${window.location.origin}/gate/login?event_id=${event.id}`;
  return (
    `Hi ${gateman.name}, you're a gateman for "${event.title}".\n\n` +
    `Login: ${url}\n` +
    `Phone: ${gateman.phone}\n` +
    `PIN: ${pin}\n\n` +
    `(One-time delivery. Save it now.)`
  );
}

function whatsappShareUrl({ event, gateman, pin }) {
  const phone = (gateman.phone || '').replace(/^\+/, '').replace(/\D/g, '');
  const text = pinShareMessage({ event, gateman, pin });
  return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
}

export default function GatemenManager() {
  const toast = useToast();
  const { eventId } = useParams();
  const [event, setEvent] = useState(null);
  const [gatemen, setGatemen] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState({ name: '', phone: '+263' });
  // PIN echo - one-time per (gatemanId, ts)
  const [pinReveal, setPinReveal] = useState(null); // { gateman, pin }

  async function reload() {
    setLoading(true);
    try {
      const [ev, gs] = await Promise.all([
        promoterGetEvent(eventId), promoterListGatemen(eventId),
      ]);
      setEvent(ev.event);
      setGatemen(gs.gatemen || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, [eventId]);

  async function onCreate(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await promoterCreateGateman(eventId, creating);
      const created = r.gateman;
      setPinReveal({ gateman: created, pin: created.pin });
      setCreating({ name: '', phone: '+263' });
      toast.success('Gateman created. Share the PIN now — it won\'t be shown again.');
      await reload();
    } catch (err) {
      toast.error(err.message || 'Failed to create');
    } finally {
      setBusy(false);
    }
  }

  async function onRegenerate(g) {
    if (!confirm(`Regenerate PIN for ${g.name}?`)) return;
    setBusy(true);
    try {
      const r = await promoterRegenerateGatemanPin(g.id);
      setPinReveal({ gateman: r.gateman, pin: r.gateman.pin });
      toast.success('New PIN generated.');
    } catch (e) { toast.error(e.message || 'Failed'); }
    finally { setBusy(false); }
  }

  async function onRevoke(g) {
    if (!confirm(`Revoke ${g.name}'s access?`)) return;
    setBusy(true);
    try {
      await promoterRevokeGateman(g.id);
      toast.success('Revoked.');
      await reload();
    } catch (e) { toast.error(e.message || 'Failed'); }
    finally { setBusy(false); }
  }

  if (loading) {
    return <div className="container-page py-16 text-inkm flex items-center gap-2 justify-center">
      <Loader2 className="animate-spin" size={16} /> Loading…
    </div>;
  }

  return (
    <main className="container-page py-8 max-w-3xl space-y-5">
      <Link to={`/promoter/events/${eventId}`} className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Back to event
      </Link>
      <h1 className="font-display text-3xl text-ink heading-accent flex items-center gap-3">
        <ShieldCheck size={28} className="text-brand" /> Gatemen
      </h1>
      <p className="text-inkm text-sm">For: <span className="text-ink">{event?.title}</span></p>

      {pinReveal && (
        <div className="card p-5 border-warning/40 space-y-3">
          <div className="text-warning text-sm font-medium uppercase tracking-wider">One-time PIN reveal</div>
          <div className="font-display text-3xl text-ink">PIN: <span className="text-brand">{pinReveal.pin}</span></div>
          <div className="text-sm text-inkm">
            For {pinReveal.gateman.name} ({pinReveal.gateman.phone}). Send it now — you can regenerate later if needed.
          </div>
          <div className="flex gap-2">
            <a href={whatsappShareUrl({ event, gateman: pinReveal.gateman, pin: pinReveal.pin })}
               target="_blank" rel="noreferrer" className="btn-primary">
              <MessageCircle size={14} /> Share on WhatsApp
            </a>
            <button className="btn-secondary"
              onClick={() => { navigator.clipboard.writeText(pinShareMessage({ event, gateman: pinReveal.gateman, pin: pinReveal.pin })); toast.success('Copied'); }}>
              Copy message
            </button>
            <button className="btn-ghost" onClick={() => setPinReveal(null)}>Dismiss</button>
          </div>
        </div>
      )}

      <div className="card p-5 space-y-3">
        <h2 className="font-display text-lg text-ink">Active gatemen</h2>
        {gatemen.length === 0 ? (
          <div className="text-inkm text-sm">None yet. Add one below.</div>
        ) : (
          <ul className="divide-y divide-bordr/60">
            {gatemen.map((g) => (
              <li key={g.id} className="py-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-ink">{g.name}</div>
                  <div className="text-xs text-inkm">{g.phone} • scans: {g.scan_count}</div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => onRegenerate(g)} disabled={busy} className="btn-secondary">
                    <KeyRound size={14} /> New PIN
                  </button>
                  <button onClick={() => onRevoke(g)} disabled={busy} className="btn-danger">
                    <Trash2 size={14} /> Revoke
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form onSubmit={onCreate} className="card p-5 space-y-3">
        <h2 className="font-display text-lg text-ink">Add gateman</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="label">Name</label>
            <input className="input-base" value={creating.name}
                   onChange={(e) => setCreating((c) => ({ ...c, name: e.target.value }))} />
          </div>
          <div>
            <label className="label">Phone</label>
            <input className="input-base" value={creating.phone}
                   onChange={(e) => setCreating((c) => ({ ...c, phone: e.target.value }))} />
          </div>
        </div>
        <p className="text-[11px] text-inkm">PIN auto-generated. You'll see it once after create.</p>
        <button type="submit" disabled={busy} className="btn-primary">
          <Plus size={14} /> Add gateman
        </button>
      </form>
    </main>
  );
}
