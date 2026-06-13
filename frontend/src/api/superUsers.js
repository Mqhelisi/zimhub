import { client } from './client.js';

export const superUsersApi = {
  list: (params = {}) => client.get('/api/super/users', { params }).then(r => r.data),
  get: (id) => client.get(`/api/super/users/${id}`).then(r => r.data),
  patchCapabilities: (id, capabilities) =>
    client.patch(`/api/super/users/${id}/capabilities`, capabilities).then(r => r.data),
  suspend: (id, reason) =>
    client.post(`/api/super/users/${id}/suspend`, { reason }).then(r => r.data),
  unsuspend: (id) => client.post(`/api/super/users/${id}/unsuspend`).then(r => r.data),
  resetPassword: (id, delivery_channels) =>
    client.post(`/api/super/users/${id}/reset-password`, { delivery_channels }).then(r => r.data),
};
