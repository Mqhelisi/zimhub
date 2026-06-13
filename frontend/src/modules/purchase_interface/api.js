// PurchaseInterface — module API client.
// Mirrors PURCHASE_INTERFACE_SPEC.md §7.
import { client as api } from '../../api/client.js';

export const purchaseInterfaceApi = {
  initiate: ({ listing_type, listing_id, quantity, domain_payload }) =>
    api.post('/api/purchases', { listing_type, listing_id, quantity, domain_payload })
      .then((r) => r.data.purchase),

  get: (id) => api.get(`/api/purchases/${id}`).then((r) => r.data.purchase),

  myPurchases: ({ role = 'buyer', status, listing_type } = {}) => {
    const params = { role };
    if (status) params.status = status;
    if (listing_type) params.listing_type = listing_type;
    return api.get('/api/my/purchases', { params }).then((r) => r.data.purchases);
  },

  whatsappLink: (id) =>
    api.post(`/api/purchases/${id}/whatsapp`).then((r) => r.data.url),

  confirmPayment: (id, { payment_ref } = {}) =>
    api.post(`/api/purchases/${id}/confirm-payment`, { payment_ref })
      .then((r) => r.data.purchase),

  confirmReceipt: (id) =>
    api.post(`/api/purchases/${id}/confirm-receipt`).then((r) => r.data.purchase),

  cancel: (id, { reason } = {}) =>
    api.post(`/api/purchases/${id}/cancel`, { reason }).then((r) => r.data.purchase),

  raiseDispute: (id, { reason }) =>
    api.post(`/api/purchases/${id}/dispute`, { reason }).then((r) => r.data.purchase),

  // Admin (super) — dispute desk.
  admin: {
    listDisputes: ({ status = 'open' } = {}) =>
      api.get('/api/admin/disputes', { params: { status } })
        .then((r) => r.data.disputes),
    getDispute: (id) =>
      api.get(`/api/admin/disputes/${id}`).then((r) => r.data.dispute),
    resolveDispute: (id, { resolution, note }) =>
      api.post(`/api/admin/disputes/${id}/resolve`, { resolution, note })
        .then((r) => r.data.dispute),
  },
};

// Human-friendly status copy
export const STATUS_LABELS = {
  awaiting_payment: 'Awaiting payment',
  awaiting_buyer_confirmation: 'Awaiting your confirmation',
  completed: 'Completed',
  cancelled: 'Cancelled',
  expired: 'Expired',
  disputed: 'Disputed',
  refunded: 'Refunded',
};

// Tone per status — drives badge & banner colors.
export const STATUS_TONE = {
  awaiting_payment: 'warning',
  awaiting_buyer_confirmation: 'info',
  completed: 'success',
  cancelled: 'muted',
  expired: 'muted',
  disputed: 'danger',
  refunded: 'muted',
};
