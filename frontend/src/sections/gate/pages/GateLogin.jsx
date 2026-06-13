import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ScanLine, Loader2 } from 'lucide-react';
import { useToast } from '../../../components/ui/Toast.jsx';
import { useGateAuth } from '../context/GateAuthContext.jsx';

export default function GateLogin() {
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthed, loading } = useGateAuth();
  const [form, setForm] = useState({ phone: '+263', pin: '', event_id: '' });
  const [busy, setBusy] = useState(false);

  // Pre-fill event_id from ?event_id= or window remembered value.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const eid = params.get('event_id');
    if (eid) setForm((f) => ({ ...f, event_id: eid }));
  }, [location.search]);

  // If already authed, jump to /gate/scan.
  useEffect(() => {
    if (isAuthed && !loading) navigate('/gate/scan', { replace: true });
  }, [isAuthed, loading, navigate]);

  async function onSubmit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await login(form);
      toast.success('Signed in. Ready to scan.');
      navigate('/gate/scan', { replace: true });
    } catch (err) {
      toast.error(err.message || 'Login failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center p-6">
      <form onSubmit={onSubmit} className="card p-6 w-full max-w-md space-y-4">
        <div className="text-center">
          <ScanLine size={42} className="mx-auto text-brand" />
          <h1 className="mt-2 font-display text-2xl text-ink heading-accent inline-block">Gate sign-in</h1>
          <p className="mt-1 text-inkm text-sm">Scoped to one event. Get your PIN from the promoter.</p>
        </div>
        <div>
          <label className="label">Phone</label>
          <input className="input-base" value={form.phone}
                 inputMode="tel" autoComplete="tel"
                 onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
        </div>
        <div>
          <label className="label">PIN</label>
          <input className="input-base" value={form.pin}
                 inputMode="numeric" autoComplete="off" maxLength={4} type="password"
                 onChange={(e) => setForm((f) => ({ ...f, pin: e.target.value.replace(/\D/g, '') }))} />
        </div>
        <div>
          <label className="label">Event ID</label>
          <input className="input-base font-mono text-xs" value={form.event_id}
                 onChange={(e) => setForm((f) => ({ ...f, event_id: e.target.value.trim() }))} />
          <p className="text-[11px] text-inkm mt-1">
            Promoter shares this via the WhatsApp invite. Or scan the QR they sent.
          </p>
        </div>
        <button type="submit" disabled={busy} className="btn-primary w-full">
          {busy ? <><Loader2 size={14} className="animate-spin" /> Signing in…</> : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
