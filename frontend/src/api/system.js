import { client } from './client.js';

export const systemApi = {
  publicConfig: () => client.get('/api/config/public').then(r => r.data),
  dashboardStats: () => client.get('/api/super/dashboard-stats').then(r => r.data),
  getConfig: () => client.get('/api/super/config').then(r => r.data),
  putConfig: (body) => client.put('/api/super/config', body).then(r => r.data),
  listMockMessages: (params = {}) =>
    client.get('/api/super/mock-messages', { params }).then(r => r.data),
};
