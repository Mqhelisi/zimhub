import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export const client = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// 401 handling — clear cached auth and redirect to /login, EXCEPT for the
// initial /api/auth/me probe which is supposed to be allowed to return 401
// without bouncing the user.
let onUnauthenticated = null;

export function setUnauthenticatedHandler(fn) {
  onUnauthenticated = fn;
}

client.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err?.response?.status === 401) {
      const url = err.config?.url || '';
      if (!url.endsWith('/api/auth/me') && !url.endsWith('auth/me')) {
        if (onUnauthenticated) onUnauthenticated();
      }
    }
    return Promise.reject(err);
  }
);

// Helper to surface backend error envelope to UI.
export function errMessage(err, fallback = 'Something went wrong.') {
  const data = err?.response?.data;
  if (data?.message) return data.message;
  if (typeof data === 'string') return data;
  return fallback;
}

export function errFieldErrors(err) {
  return err?.response?.data?.field_errors || null;
}
