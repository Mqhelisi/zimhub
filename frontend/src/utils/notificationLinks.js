// Derive a destination path from a notification's metadata. Returns null when
// the notification isn't actionable (e.g. Stage 1 welcome/announcement kinds).
//
// Stage 2 — purchase- and dispute-related notifications route to the purchase
// detail page. Admins can reach the dispute desk via the sidebar from there.
export function notificationLink(n) {
  if (!n) return null;
  const meta = n.metadata || {};
  const pid = meta.purchase_id;
  const did = meta.dispute_id;
  const reqId = meta.signup_request_id;

  const purchaseKinds = new Set([
    'purchase_initiated',
    'payment_confirmed',
    'purchase_completed',
    'purchase_cancelled',
    'purchase_expired',
    'purchase_disputed',
    'dispute_resolved',
  ]);

  if (purchaseKinds.has(n.kind)) {
    if (pid) return `/purchases/${pid}`;
    if (did) return `/super/disputes/${did}`;
  }
  // Stage 1 — super admin can jump straight to the signup request.
  if (n.kind === 'new_signup_request' && reqId) {
    return `/super/signup-requests/${reqId}`;
  }
  // Stage 4 — BookingInterface notifications route to the buyer's booking
  // detail; booking-dispute kinds go to the BI desk for admins (the
  // booking_dispute_id is only set on the admin copy).
  const bookingKinds = new Set([
    'booking_requested',
    'booking_confirmed',
    'booking_declined',
    'booking_cancelled',
    'booking_expired',
    'booking_completed',
    'booking_no_show',
    'dispute_raised',
  ]);
  const bookingId = meta.booking_id;
  const bookingDisputeId = meta.booking_dispute_id;
  if (bookingDisputeId) return `/super/booking-disputes/${bookingDisputeId}`;
  if (bookingKinds.has(n.kind) && bookingId) return `/my/bookings/${bookingId}`;
  if (n.kind === 'dispute_resolved' && bookingId) return `/my/bookings/${bookingId}`;

  // Generic fallback: if there's a purchase_id anyway, use it.
  if (pid) return `/purchases/${pid}`;
  if (bookingId) return `/my/bookings/${bookingId}`;
  return null;
}
