// Gate scanner API — bearer token in localStorage.
// This is the ONE non-cookie auth surface in ZimHub (Stage 3 §5.5).
// Dev fallback mirrors Stage 2's /src/api/client.js — direct to Flask :5000.
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
const TOKEN_KEY = 'zimhub_gate_token';
const META_KEY  = 'zimhub_gate_meta';

export function getGateToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function getGateMeta() {
  try {
    const v = localStorage.getItem(META_KEY);
    return v ? JSON.parse(v) : null;
  } catch { return null; }
}
export function setGateSession(token, meta) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(META_KEY, JSON.stringify(meta || {}));
  } catch (_) {}
}
export function clearGateSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(META_KEY);
  } catch (_) {}
}

async function gateReq(method, path, body) {
  const token = getGateToken();
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method, headers,
    body: body == null ? undefined : JSON.stringify(body),
  });
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : null;
  if (!res.ok) {
    const err = new Error((data && data.error?.message) || res.statusText);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

export function gateLogin({ phone, pin, event_id }) {
  return gateReq('POST', '/api/gate/login', { phone, pin, event_id });
}
export function gateMe() { return gateReq('GET', '/api/gate/me'); }
export function gateScan(qr_payload, extras = {}) {
  return gateReq('POST', '/api/gate/scan', { qr_payload, ...extras });
}
export function gateManifest(eventId) {
  return gateReq('GET', `/api/gate/event/${eventId}/manifest`);
}
