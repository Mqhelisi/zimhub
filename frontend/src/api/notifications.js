import { client } from './client.js';

export const notificationsApi = {
  list: (params = {}) => client.get('/api/notifications', { params }).then(r => r.data),
  markRead: (id) => client.post(`/api/notifications/${id}/read`).then(r => r.data),
  markAllRead: () => client.post('/api/notifications/read-all').then(r => r.data),
};
