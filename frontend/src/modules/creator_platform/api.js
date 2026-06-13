// CreatorPlatform API (cookie auth, same convention as the events module).
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

async function req(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: body == null ? undefined : JSON.stringify(body),
  });
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : null;
  if (!res.ok) {
    const err = new Error((data && (data.message || data.error?.message)) || res.statusText);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

async function upload(path, file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST', credentials: 'include', body: fd,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.message) || 'Upload failed');
  return data;
}

export const creatorApi = {
  // ---- Public ----
  listCreators: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.type) qs.set('type', params.type);
    if (params.q) qs.set('q', params.q);
    return req('GET', `/api/creators${qs.toString() ? '?' + qs : ''}`);
  },
  getCreator: (slug) => req('GET', `/api/creators/${slug}`),
  getCreatorTracks: (slug) => req('GET', `/api/creators/${slug}/tracks`),
  getCreatorGallery: (slug) => req('GET', `/api/creators/${slug}/gallery`),
  getCreatorEvents: (slug) => req('GET', `/api/creators/${slug}/events`),
  types: () => req('GET', '/api/creators/types'),
  landing: () => req('GET', '/api/creators/landing'),
  search: (q, type = 'all') =>
    req('GET', `/api/creators/search?q=${encodeURIComponent(q)}&type=${type}`),
  recordPlay: (trackId, sessionId) =>
    req('POST', `/api/creators/tracks/${trackId}/play`, { session_id: sessionId }),

  // ---- Studio ----
  dashboard: () => req('GET', '/api/creator/dashboard'),
  getProfile: () => req('GET', '/api/creator/profile'),
  updateProfile: (body) => req('PUT', '/api/creator/profile', body),

  listTracks: () => req('GET', '/api/creator/tracks'),
  createTrack: (body) => req('POST', '/api/creator/tracks', body),
  editTrack: (id, body) => req('PATCH', `/api/creator/tracks/${id}`, body),
  deleteTrack: (id) => req('DELETE', `/api/creator/tracks/${id}`),
  reorderTracks: (ids) => req('POST', '/api/creator/tracks/reorder', { track_ids: ids }),

  listGallery: () => req('GET', '/api/creator/gallery'),
  createCollection: (body) => req('POST', '/api/creator/gallery/collections', body),
  editCollection: (id, body) => req('PATCH', `/api/creator/gallery/collections/${id}`, body),
  deleteCollection: (id) => req('DELETE', `/api/creator/gallery/collections/${id}`),
  createItem: (body) => req('POST', '/api/creator/gallery/items', body),
  editItem: (id, body) => req('PATCH', `/api/creator/gallery/items/${id}`, body),
  deleteItem: (id) => req('DELETE', `/api/creator/gallery/items/${id}`),

  listEvents: () => req('GET', '/api/creator/events'),
  createEvent: (body) => req('POST', '/api/creator/events', body),
  getEvent: (id) => req('GET', `/api/creator/events/${id}`),
  editEvent: (id, body) => req('PATCH', `/api/creator/events/${id}`, body),
  deleteEvent: (id) => req('DELETE', `/api/creator/events/${id}`),
  addTicketType: (id, body) => req('POST', `/api/creator/events/${id}/ticket-types`, body),
  listGatemen: (id) => req('GET', `/api/creator/events/${id}/gatemen`),
  createGateman: (id, body) => req('POST', `/api/creator/events/${id}/gatemen`, body),
  attendees: (id) => req('GET', `/api/creator/events/${id}/attendees`),

  // ---- Uploads ----
  uploadImage: (file) => upload('/api/creator/uploads/image', file),
  uploadAudio: (file) => upload('/api/creator/uploads/audio', file),
};
