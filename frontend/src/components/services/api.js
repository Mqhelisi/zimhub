// Services section API — public discovery (/api/services/*) and the
// provider admin surface (/api/provider/* owned by services_section).
import { client } from '../../api/client.js';

// ----- Public -------------------------------------------------------------
export async function servicesHome() {
  const { data } = await client.get('/api/services/home');
  return data;
}

export async function listProviders(params = {}) {
  const { data } = await client.get('/api/services/providers', { params });
  return data;
}

export async function providerBySlug(slug) {
  const { data } = await client.get(`/api/services/providers/${slug}`);
  return data;
}

export async function providerAvailability(slug, fromIso, toIso) {
  const { data } = await client.get(`/api/services/providers/${slug}/availability`, {
    params: { from: fromIso, to: toIso },
  });
  return data; // {available_slots, booked_slots}
}

// ----- Provider admin -------------------------------------------------------
export async function getProviderProfile() {
  const { data } = await client.get('/api/provider/profile');
  return data.profile;
}
export async function updateProviderProfile(payload) {
  const { data } = await client.put('/api/provider/profile', payload);
  return data.profile;
}
export async function listMyServices(params = {}) {
  const { data } = await client.get('/api/provider/services', { params });
  return data.services;
}
export async function getMyService(id) {
  const { data } = await client.get(`/api/provider/services/${id}`);
  return data.service;
}
export async function createService(payload) {
  const { data } = await client.post('/api/provider/services', payload);
  return data.service;
}
export async function updateService(id, payload) {
  const { data } = await client.put(`/api/provider/services/${id}`, payload);
  return data.service;
}
export async function archiveService(id) {
  await client.delete(`/api/provider/services/${id}`);
}
export async function providerDashboard() {
  const { data } = await client.get('/api/provider/dashboard');
  return data;
}
export async function uploadProviderImage(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/api/provider/uploads/image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.url;
}
