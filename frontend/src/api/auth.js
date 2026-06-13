import { client } from './client.js';

export const authApi = {
  signup: (body) => client.post('/api/auth/signup', body).then(r => r.data),
  login: (email, password) => client.post('/api/auth/login', { email, password }).then(r => r.data),
  logout: () => client.post('/api/auth/logout').then(r => r.data),
  me: () => client.get('/api/auth/me').then(r => r.data),
  passwordChange: (current_password, new_password) =>
    client.post('/api/auth/password-change', { current_password, new_password }).then(r => r.data),
  passwordResetRequest: (email) =>
    client.post('/api/auth/password-reset/request', { email }).then(r => r.data),
  passwordResetConfirm: (token, new_password) =>
    client.post('/api/auth/password-reset/confirm', { token, new_password }).then(r => r.data),
};
