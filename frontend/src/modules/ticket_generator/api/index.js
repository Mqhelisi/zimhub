// Events + ticket APIs (main app: cookie auth).
//
// Dev fallback hits Flask on :5000 directly — same convention as Stage 2's
// /src/api/client.js. In production, set VITE_API_BASE_URL to your deployed
// API origin (e.g. `https://api.zimhub.co.zw`) before `npm run build`.
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

async function req(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
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

// ---- Public ---------------------------------------------------------------
export function listEvents(params = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set('category', params.category);
  if (params.mode) qs.set('mode', params.mode);
  if (params.date_from) qs.set('date_from', params.date_from);
  if (params.date_to) qs.set('date_to', params.date_to);
  if (params.q) qs.set('q', params.q);
  if (params.timing) qs.set('timing', params.timing);
  if (params.page) qs.set('page', String(params.page));
  return req('GET', `/api/events${qs.toString() ? '?' + qs : ''}`);
}
export function getEvent(id) { return req('GET', `/api/events/${id}`); }
export function listCategories() { return req('GET', '/api/events/categories'); }
export function topRanking() { return req('GET', '/api/events/top'); }

// ---- Buyer tickets --------------------------------------------------------
export function listMyTickets() { return req('GET', '/api/my/tickets'); }
export function getTicket(id)   { return req('GET', `/api/tickets/${id}`); }
export function resendTicket(id){ return req('POST', `/api/tickets/${id}/resend`); }

// ---- Promoter -------------------------------------------------------------
export function promoterListEvents(filters = {}) {
  const qs = new URLSearchParams();
  if (filters.status) qs.set('status', filters.status);
  if (filters.mode) qs.set('mode', filters.mode);
  if (filters.timing) qs.set('timing', filters.timing);
  return req('GET', `/api/promoter/events${qs.toString() ? '?' + qs : ''}`);
}
export function promoterGetEvent(id) { return req('GET', `/api/promoter/events/${id}`); }
export function promoterDashboard() { return req('GET', '/api/promoter/dashboard'); }
export function promoterProfile() { return req('GET', '/api/promoter/profile'); }
export function promoterUpdateProfile(body) { return req('PUT', '/api/promoter/profile', body); }

export function promoterCreateTicketedEvent(body) { return req('POST', '/api/promoter/events', body); }
export function promoterEditTicketedEvent(id, body) { return req('PATCH', `/api/promoter/events/${id}`, body); }
export function promoterPublishEvent(id) { return req('POST', `/api/promoter/events/${id}/publish`); }
export function promoterCancelEvent(id) { return req('POST', `/api/promoter/events/${id}/cancel`); }

export function promoterCreateFlyerEvent(body) { return req('POST', '/api/promoter/events/flyer', body); }
export function promoterEditFlyerEvent(id, body) { return req('PUT', `/api/promoter/events/${id}`, body); }
export function promoterConvertToTicketed(id, body) {
  return req('POST', `/api/promoter/events/${id}/convert-to-ticketed`, body);
}

export function promoterAddTicketType(eventId, body) {
  return req('POST', `/api/promoter/events/${eventId}/ticket-types`, body);
}
export function promoterEditTicketType(ttId, body) {
  return req('PATCH', `/api/promoter/ticket-types/${ttId}`, body);
}
export function promoterDeleteTicketType(ttId) {
  return req('DELETE', `/api/promoter/ticket-types/${ttId}`);
}

export function promoterAttendees(eventId) {
  return req('GET', `/api/promoter/events/${eventId}/attendees`);
}
export function promoterAttendeesCsvUrl(eventId, scope = 'all') {
  return `${API_BASE}/api/promoter/events/${eventId}/attendees.csv?scope=${encodeURIComponent(scope)}`;
}

export function promoterListGatemen(eventId) {
  return req('GET', `/api/promoter/events/${eventId}/gatemen`);
}
export function promoterCreateGateman(eventId, body) {
  return req('POST', `/api/promoter/events/${eventId}/gatemen`, body);
}
export function promoterRegenerateGatemanPin(gmId) {
  return req('POST', `/api/promoter/gatemen/${gmId}/regenerate-pin`);
}
export function promoterRevokeGateman(gmId) {
  return req('DELETE', `/api/promoter/gatemen/${gmId}`);
}

export async function promoterUploadImage(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}/api/promoter/uploads/image`, {
    method: 'POST', credentials: 'include', body: fd,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || 'Upload failed');
  return data.url;
}
