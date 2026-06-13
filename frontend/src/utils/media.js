// Resolve a media URL (audio/image) to something the browser can fetch.
//
// - Absolute URLs (Cloudinary in prod, picsum seed images) pass through.
// - Relative paths (dev seed audio like `/local_uploads/seed/audio/x.mp3`) are
//   resolved against the API origin, since the API serves /local_uploads/* with
//   HTTP range support (so the player's seek bar works).
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export function mediaUrl(url) {
  if (!url) return '';
  if (/^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) {
    return url;
  }
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
}
