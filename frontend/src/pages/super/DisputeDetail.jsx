import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { formatRelative } from '../../utils/time.js';
import { purchaseInterfaceApi } from '../../modules/purchase_interface/api.js';
import { PurchaseStatusBadge } from '../../modules/purchase_interface/primitives/PurchaseStatusBadge.jsx';
import { PurchaseEventTimeline } from '../../modules/purchase_interface/primitives/PurchaseEventTimeline.jsx';
import { DisputeBanner } from '../../modules/purchase_interface/primitives/DisputeBanner.jsx';

export default function DisputeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [dispute, setDispute] = useState(null);
  const [error, setError] = useState('');
  const [resolution, setResolution] = useState('completed');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let alive = true;
    purchaseInterfaceApi.admin.getDispute(id)
      .then((d) => alive && setDispute(d))
      .catch((e) => alive && setError(e?.response?.data?.message || 'Could not load dispute.'));
    return () => { alive = false; };
  }, [id]);

  if (error) {
    return (
      <div>
        <Link to="/super/disputes" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
          <ArrowLeft size={14} /> Disputes
        </Link>
        <p className="mt-4 text-danger">{error}</p>
      </div>
    );
  }
  if (!dispute) return <div className="flex justify-center py-10"><Spinner size={22} /></div>;

  const p = dispute.purchase || {};
  const items = p.domain_payload?.items || [];

  async function resolve() {
    setSubmitting(true);
    try {
      const updated = await purchaseInterfaceApi.admin.resolveDispute(id, { resolution, note: note || undefined });
      setDispute(updated);
      toast.success(`Dispute resolved as ${resolution}.`);
    } catch (e) {
      toast.error(e?.response?.data?.message || 'Could not resolve.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Link to="/super/disputes" className="text-sm text-inkm hover:text-ink inline-flex items-center gap-1">
        <ArrowLeft size={14} /> Disputes
      </Link>

      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="font-display text-3xl text-ink">
          Dispute <span className="text-2xl text-inkm">#{id.slice(0, 8)}</span>
        </h1>
        <PurchaseStatusBadge status={p.status} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <DisputeBanner dispute={dispute} />

          <Card>
            <h2 className="font-display text-xl text-ink">Purchase</h2>
            <div className="mt-3 text-sm space-y-1">
              <div className="text-inkm">Buyer: <span className="text-ink">{p.buyer?.name}</span> ({p.buyer?.phone})</div>
              <div className="text-inkm">Seller: <span className="text-ink">{p.seller?.shop_name || p.seller?.name}</span> ({p.seller?.phone})</div>
              <div className="text-inkm">Total: <span className="text-ink">${p.total_usd}</span></div>
              {p.payment_ref && <div className="text-inkm">Payment ref: <span className="text-ink">{p.payment_ref}</span></div>}
              {p.created_at && <div className="text-inkm">Created {formatRelative(p.created_at)}</div>}
            </div>

            <ul className="mt-4 divide-y divide-bordr">
              {items.map((it, i) => (
                <li key={i} className="py-2 flex items-center gap-3">
                  {it.photo && (
                    <img src={it.photo} alt=""
                         className="h-10 w-10 rounded-md object-cover ring-1 ring-bordr" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="truncate text-ink">{it.name}</div>
                    <div className="text-xs text-inkm">
                      {it.qty} × ${Number(it.unit_price_usd || 0).toFixed(2)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>

            <Link
              to={`/purchases/${p.id}`}
              className="mt-3 inline-block text-sm text-brand hover:underline"
            >
              Open full purchase →
            </Link>
          </Card>

          <Card>
            <h2 className="font-display text-xl text-ink">Activity</h2>
            <div className="mt-3">
              <PurchaseEventTimeline events={p.events || []} />
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          {dispute.status === 'open' ? (
            <Card>
              <h2 className="font-display text-xl text-ink flex items-center gap-2">
                <ShieldCheck size={18} className="text-brand" /> Resolve
              </h2>
              <Select
                label="Resolution"
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="mt-3"
              >
                <option value="completed">Mark complete (buyer accepts goods)</option>
                <option value="refunded">Refund (admin to process manually)</option>
                <option value="cancelled">Cancel (stock restored, no money owed)</option>
              </Select>
              <Textarea
                label="Note (optional)"
                rows={3}
                placeholder="What you decided and why. Both parties will see this."
                value={note}
                onChange={(e) => setNote(e.target.value)}
                className="mt-3"
              />
              <Button
                variant="primary"
                onClick={resolve}
                disabled={submitting}
                className="mt-4 w-full justify-center"
              >
                {submitting ? 'Resolving…' : 'Submit resolution'}
              </Button>
            </Card>
          ) : (
            <Card className="!bg-bgs2/40">
              <h2 className="font-display text-xl text-ink">Resolved</h2>
              <p className="mt-2 text-sm text-inkm">
                Resolution: <span className="text-ink">{dispute.resolution}</span>
                {dispute.resolved_at ? ` • ${formatRelative(dispute.resolved_at)}` : ''}
              </p>
              {dispute.resolution_note && (
                <p className="mt-2 text-sm text-inkm whitespace-pre-wrap">{dispute.resolution_note}</p>
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
