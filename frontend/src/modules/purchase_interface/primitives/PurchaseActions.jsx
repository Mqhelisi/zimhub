import React, { useState } from 'react';
import { MessageCircle, Check, X, AlertTriangle, BadgeCheck } from 'lucide-react';
import { Button } from '../../../components/ui/Button.jsx';
import { Modal } from '../../../components/ui/Modal.jsx';
import { Input } from '../../../components/ui/Input.jsx';
import { Textarea } from '../../../components/ui/Textarea.jsx';
import { useToast } from '../../../components/ui/Toast.jsx';
import { purchaseInterfaceApi } from '../api.js';

/**
 * Renders the buttons relevant to the current viewer/status. The Purchase
 * detail page passes `permitted_actions` from the backend (purchase.permitted_actions).
 *
 * Props:
 *   purchase
 *   onChanged(newPurchase)   — called after any successful mutation
 */
export function PurchaseActions({ purchase, onChanged }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [confirmPayment, setConfirmPayment] = useState(false);
  const [paymentRef, setPaymentRef] = useState('');
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [disputeOpen, setDisputeOpen] = useState(false);
  const [disputeReason, setDisputeReason] = useState('');

  const actions = purchase?.permitted_actions || [];

  async function handleWhatsApp() {
    try {
      const url = await purchaseInterfaceApi.whatsappLink(purchase.id);
      if (url) window.open(url, '_blank', 'noopener,noreferrer');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not generate WhatsApp link.');
    }
  }

  async function doConfirmPayment() {
    setBusy(true);
    try {
      const p = await purchaseInterfaceApi.confirmPayment(purchase.id, { payment_ref: paymentRef || undefined });
      onChanged?.(p);
      toast.success('Payment confirmed.');
      setConfirmPayment(false);
      setPaymentRef('');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not confirm payment.');
    } finally { setBusy(false); }
  }

  async function doConfirmReceipt() {
    setBusy(true);
    try {
      const p = await purchaseInterfaceApi.confirmReceipt(purchase.id);
      onChanged?.(p);
      toast.success('Receipt confirmed. Purchase complete.');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not confirm receipt.');
    } finally { setBusy(false); }
  }

  async function doCancel() {
    setBusy(true);
    try {
      const p = await purchaseInterfaceApi.cancel(purchase.id, { reason: cancelReason || undefined });
      onChanged?.(p);
      toast.success('Purchase cancelled.');
      setCancelOpen(false);
      setCancelReason('');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not cancel.');
    } finally { setBusy(false); }
  }

  async function doDispute() {
    if (!disputeReason.trim()) { toast.error('A reason is required.'); return; }
    setBusy(true);
    try {
      const p = await purchaseInterfaceApi.raiseDispute(purchase.id, { reason: disputeReason.trim() });
      onChanged?.(p);
      toast.success('Dispute raised. A ZimHub admin will review.');
      setDisputeOpen(false);
      setDisputeReason('');
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not raise dispute.');
    } finally { setBusy(false); }
  }

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {actions.includes('whatsapp') && (
          <Button variant="primary" onClick={handleWhatsApp} className="!bg-success !border-success">
            <MessageCircle size={16} /> WhatsApp counterparty
          </Button>
        )}
        {actions.includes('confirm_payment') && (
          <Button variant="primary" onClick={() => setConfirmPayment(true)}>
            <BadgeCheck size={16} /> I've received payment
          </Button>
        )}
        {actions.includes('confirm_receipt') && (
          <Button variant="primary" onClick={doConfirmReceipt} disabled={busy}>
            <Check size={16} /> I've received the goods
          </Button>
        )}
        {actions.includes('cancel') && (
          <Button variant="secondary" onClick={() => setCancelOpen(true)} disabled={busy}>
            <X size={16} /> Cancel
          </Button>
        )}
        {actions.includes('dispute') && (
          <Button variant="secondary" onClick={() => setDisputeOpen(true)}
                  className="!border-danger/40 !text-danger hover:!bg-danger/5" disabled={busy}>
            <AlertTriangle size={16} /> Raise dispute
          </Button>
        )}
      </div>

      <Modal open={confirmPayment} onClose={() => setConfirmPayment(false)} title="Confirm payment received">
        <p className="text-sm text-inkm">
          Only confirm after the buyer's Ecocash payment has actually landed and you've prepared/delivered the goods.
          Optionally paste the Ecocash reference.
        </p>
        <Input
          label="Payment reference (optional)"
          placeholder="e.g. ECOXXXX1234"
          value={paymentRef}
          onChange={(e) => setPaymentRef(e.target.value)}
          className="mt-3"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setConfirmPayment(false)} disabled={busy}>Cancel</Button>
          <Button variant="primary" onClick={doConfirmPayment} disabled={busy}>Confirm payment</Button>
        </div>
      </Modal>

      <Modal open={cancelOpen} onClose={() => setCancelOpen(false)} title="Cancel this purchase?">
        <p className="text-sm text-inkm">
          You can only cancel while no payment has been confirmed yet. After cancellation the reservation is released.
        </p>
        <Textarea
          label="Reason (optional)"
          rows={2}
          value={cancelReason}
          onChange={(e) => setCancelReason(e.target.value)}
          className="mt-3"
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setCancelOpen(false)} disabled={busy}>Keep purchase</Button>
          <Button variant="primary" onClick={doCancel} disabled={busy}>Cancel purchase</Button>
        </div>
      </Modal>

      <Modal open={disputeOpen} onClose={() => setDisputeOpen(false)} title="Raise a dispute">
        <p className="text-sm text-inkm">
          A ZimHub admin will review and decide on completion, refund, or cancellation. Be specific —
          what was promised vs. what happened, plus dates if helpful.
        </p>
        <Textarea
          label="What went wrong?"
          rows={4}
          value={disputeReason}
          onChange={(e) => setDisputeReason(e.target.value)}
          className="mt-3"
          required
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDisputeOpen(false)} disabled={busy}>Not yet</Button>
          <Button variant="primary" onClick={doDispute} disabled={busy}>Submit dispute</Button>
        </div>
      </Modal>
    </>
  );
}
