import { client } from './client.js';

export const signupRequestsApi = {
  submit: (body) => client.post('/api/signup-requests', body).then(r => r.data),
  list: (params = {}) =>
    client.get('/api/super/signup-requests', { params }).then(r => r.data),
  get: (id) => client.get(`/api/super/signup-requests/${id}`).then(r => r.data),
  approve: (id, credential_delivery_channels) =>
    client.post(`/api/super/signup-requests/${id}/approve`, { credential_delivery_channels })
          .then(r => r.data),
  reject: (id, reason) =>
    client.post(`/api/super/signup-requests/${id}/reject`, { reason }).then(r => r.data),
};
