import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle2, AlertTriangle, XCircle, ShieldX, RefreshCw } from 'lucide-react';
import { useGateAuth } from '../context/GateAuthContext.jsx';
import { gateScan } from '../api/index.js';

// We import html5-qrcode lazily so the bundle doesn't pay for it on every page.
async function loadHtml5Qrcode() {
  const mod = await import('html5-qrcode');
  return mod.Html5Qrcode;
}

const RESULT_HOLD_MS = 1800;   // feedback overlay duration
const DEDUP_WINDOW_MS = 2500;  // same payload skipped within this window

function deviceId() {
  // Persistent best-effort device id; not security-sensitive.
  let v = null;
  try { v = localStorage.getItem('zimhub_gate_device_id'); } catch (_) {}
  if (!v) {
    v = 'gate-' + Math.random().toString(36).slice(2, 8);
    try { localStorage.setItem('zimhub_gate_device_id', v); } catch (_) {}
  }
  return v;
}

function FeedbackOverlay({ result, onDismiss }) {
  if (!result) return null;
  let cls = 'admit', Icon = CheckCircle2, title = 'ADMIT', sub = 'Welcome.';
  if (result.result === 'already_used') {
    cls = 'already'; Icon = AlertTriangle; title = 'ALREADY SCANNED';
    sub = result.original_checkin
      ? `First scan at ${new Date(result.original_checkin.time).toLocaleString('en-ZW', { hour: '2-digit', minute: '2-digit' })} by ${result.original_checkin.gateman_name || 'gateman'}`
      : 'Ticket already used.';
  } else if (result.result === 'voided') {
    cls = 'deny'; Icon = XCircle; title = 'VOIDED'; sub = 'Do not admit.';
  } else if (result.result === 'wrong_event') {
    cls = 'deny'; Icon = ShieldX; title = 'WRONG EVENT'; sub = 'Ticket is for a different event.';
  } else if (result.result === 'invalid_signature') {
    cls = 'deny'; Icon = ShieldX; title = 'FAKE'; sub = 'QR signature failed.';
  } else if (result.result === 'invalid') {
    cls = 'deny'; Icon = ShieldX; title = 'INVALID'; sub = 'Ticket not found.';
  }
  const t = result.ticket || {};
  return (
    <div className={`gate-feedback ${cls}`} onClick={onDismiss}>
      <Icon size={96} />
      <div className="mt-4 text-4xl font-bold tracking-wide">{title}</div>
      <div className="mt-2 text-lg opacity-90 max-w-md text-center px-6">{sub}</div>
      {t.attendee_name && (
        <div className="mt-4 text-base opacity-90">
          {t.attendee_name}{t.ticket_type ? ` • ${t.ticket_type.name}` : ''}
        </div>
      )}
      <button className="mt-6 px-4 py-2 rounded-md bg-black/30 text-white text-sm">
        Tap to continue
      </button>
    </div>
  );
}

export default function GateScan() {
  const navigate = useNavigate();
  const { meta, isAuthed, loading } = useGateAuth();
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(true);

  const scannerRef = useRef(null);
  const lastScanRef = useRef({ payload: null, ts: 0 });
  const busyRef = useRef(false);
  const dismissTimerRef = useRef(null);

  useEffect(() => {
    if (!loading && !isAuthed) navigate('/gate/login', { replace: true });
  }, [isAuthed, loading, navigate]);

  const handleResult = useCallback((scanResult) => {
    setResult(scanResult);
    if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    dismissTimerRef.current = setTimeout(() => setResult(null), RESULT_HOLD_MS);
  }, []);

  const onPayload = useCallback(async (payload) => {
    const now = Date.now();
    if (busyRef.current) return;
    if (lastScanRef.current.payload === payload &&
        now - lastScanRef.current.ts < DEDUP_WINDOW_MS) {
      return;
    }
    lastScanRef.current = { payload, ts: now };
    busyRef.current = true;
    try {
      const r = await gateScan(payload, { device_id: deviceId() });
      handleResult(r);
    } catch (e) {
      handleResult({ result: 'invalid', message: e.message || 'Network error' });
    } finally {
      busyRef.current = false;
    }
  }, [handleResult]);

  useEffect(() => {
    let html5qr = null;
    let running = true;

    (async () => {
      try {
        const Html5Qrcode = await loadHtml5Qrcode();
        if (!running) return;
        html5qr = new Html5Qrcode('zimhub-gate-reader', /* verbose= */ false);
        scannerRef.current = html5qr;
        await html5qr.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 280, height: 280 }, aspectRatio: 1.0 },
          (decodedText) => onPayload(decodedText),
          (_err) => {},  // per-frame decode errors; silent.
        );
        setStarting(false);
      } catch (e) {
        setError(e?.message || 'Camera not available. Use a phone with camera access enabled.');
        setStarting(false);
      }
    })();

    return () => {
      running = false;
      const inst = scannerRef.current;
      scannerRef.current = null;
      if (inst) {
        try {
          inst.stop().catch(() => {}).finally(() => {
            try { inst.clear(); } catch (_) {}
          });
        } catch (_) {}
      }
      if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    };
  }, [onPayload]);

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-inkm gap-2">
      <Loader2 className="animate-spin" size={16} /> Loading…
    </div>;
  }

  return (
    <main className="flex-1 flex flex-col items-center justify-start p-4 gap-4">
      <div className="w-full max-w-md text-center">
        <div className="text-inkm text-sm">Point the camera at a ticket QR.</div>
        <div className="text-xs text-inkm mt-0.5">{meta?.event?.title}</div>
      </div>
      <div className="relative w-full max-w-md aspect-square rounded-xl overflow-hidden border border-bordr bg-black">
        <div id="zimhub-gate-reader" className="w-full h-full" />
        {starting && (
          <div className="absolute inset-0 flex items-center justify-center text-inkm">
            <Loader2 className="animate-spin" size={20} />
          </div>
        )}
      </div>

      {error && (
        <div className="card border-danger/40 p-4 max-w-md w-full text-danger text-sm flex items-center gap-2">
          <ShieldX size={16} /> {error}
        </div>
      )}

      <FeedbackOverlay result={result} onDismiss={() => setResult(null)} />

      <button onClick={() => {
        // Manual reset of dedup so the same QR can be re-scanned immediately.
        lastScanRef.current = { payload: null, ts: 0 };
        setResult(null);
      }} className="btn-ghost mt-2">
        <RefreshCw size={14} /> Reset
      </button>
    </main>
  );
}
