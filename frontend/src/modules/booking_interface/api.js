// BookingInterface frontend API — mirrors BI spec §8.
import { client } from '../../api/client.js';

// ----- Requester / public ------------------------------------------------
export async function createBooking(payload) {
  const { data } = await client.post('/api/bookings', payload);
  return data.booking;
}

export async function getBooking(id) {
  const { data } = await client.get(`/api/bookings/${id}`);
  return data.booking;
}

export async function myBookings({ role = 'requester', status = '' } = {}) {
  const { data } = await client.get('/api/my/bookings', { params: { role, status } });
  return data.bookings;
}

export async function whatsappLink(id) {
  const { data } = await client.post(`/api/bookings/${id}/whatsapp`);
  return data.url;
}

// ----- Transitions --------------------------------------------------------
export async function acceptBooking(id) {
  const { data } = await client.post(`/api/bookings/${id}/accept`);
  return data.booking;
}
export async function declineBooking(id, reason) {
  const { data } = await client.post(`/api/bookings/${id}/decline`, { reason });
  return data.booking;
}
export async function cancelBooking(id, reason) {
  const { data } = await client.post(`/api/bookings/${id}/cancel`, { reason });
  return data.booking;
}
export async function markNoShow(id) {
  const { data } = await client.post(`/api/bookings/${id}/no-show`);
  return data.booking;
}
export async function markComplete(id) {
  const { data } = await client.post(`/api/bookings/${id}/complete`);
  return data.booking;
}
export async function raiseDispute(id, reason) {
  const { data } = await client.post(`/api/bookings/${id}/dispute`, { reason });
  return data;
}

// ----- Provider availability + calendar (BI-owned endpoints) -------------
export async function listRules() {
  const { data } = await client.get('/api/provider/availability/rules');
  return data.rules;
}
export async function addRule(rule) {
  const { data } = await client.post('/api/provider/availability/rules', rule);
  return data.rule;
}
export async function deleteRule(id) {
  await client.delete(`/api/provider/availability/rules/${id}`);
}
export async function listBlocks(params = {}) {
  const { data } = await client.get('/api/provider/availability/blocks', { params });
  return data.blocks;
}
export async function addBlock(block) {
  const { data } = await client.post('/api/provider/availability/blocks', block);
  return data.block;
}
export async function deleteBlock(id) {
  await client.delete(`/api/provider/availability/blocks/${id}`);
}
export async function providerCalendar(fromIso, toIso) {
  const { data } = await client.get('/api/provider/calendar', {
    params: { from: fromIso, to: toIso },
  });
  return data; // {bookings, availability_rules, time_blocks}
}

// ----- Admin dispute desk -------------------------------------------------
export async function listBookingDisputes(status = 'open') {
  const { data } = await client.get('/api/admin/booking-disputes', { params: { status } });
  return data.disputes;
}
export async function getBookingDispute(id) {
  const { data } = await client.get(`/api/admin/booking-disputes/${id}`);
  return data.dispute;
}
export async function resolveBookingDispute(id, resolution, note) {
  const { data } = await client.post(`/api/admin/booking-disputes/${id}/resolve`, {
    resolution, note,
  });
  return data.dispute;
}
