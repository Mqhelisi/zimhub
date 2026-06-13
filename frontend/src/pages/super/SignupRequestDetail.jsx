import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, X, Copy } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Badge } from '../../components/ui/Badge.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Modal } from '../../components/ui/Modal.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { signupRequestsApi } from '../../api/signupRequests.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { formatDateTime } from '../../utils/time.js';
import { errMessage } from '../../api/client.js';

function PayloadDisplay({ payload }) {
  if (!payload) return null;
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {Object.entries(payload).map(([k, v]) => (
        <div key={k}>
          <dt className="text-[10px] font-medium uppercase tracking-wider text-inkm">{k.replace(/_/g, ' ')}</dt>
          <dd className="mt-0.5 text-sm text-ink break-words">
            {Array.isArray(v) ? (v.length ? v.join(', ') : '—') : (v ?? '—')}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function SignupRequestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [req, setReq] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Approve modal
  const [approveOpen, setApproveOpen] = useState(false);
  const [emailChannel, setEmailChannel] = useState(true);
  const [whatsappChannel, setWhatsappChannel] = useState(false);
  const [approving, setApproving] = useState(false);

  // Reject modal
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [rejecting, setRejecting] = useState(false);

  // Temp password reveal
  const [tempPwResult, setTempPwResult] = useState(null);

  useEffect(() => {
    setLoading(true);
    signupRequestsApi.get(id)
      .then((d) => { setReq(d.request); setError(''); })
      .catch((e) => setError(e?.response?.data?.message || 'Not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>;
  if (error) return <div className="text-danger">{error}</div>;
  if (!req) return null;

  const approve = async () => {
    setApproving(true);
    try {
      const channels = [];
      if (emailChannel) channels.push('email');
      if (whatsappChannel) channels.push('whatsapp');
      if (channels.length === 0) {
        toast.error('Pick at least one delivery channel.');
        setApproving(false);
        return;
      }
      const r = await signupRequestsApi.approve(req.id, channels);
      setApproveOpen(false);
      setTempPwResult({ password: r.temp_password, channels: r.delivery_channels });
      const updated = await signupRequestsApi.get(req.id);
      setReq(updated.request);
      toast.success('Application approved', `Credentials dispatched via ${r.delivery_channels.join(' + ')}.`);
    } catch (e) {
      toast.error('Could not approve', errMessage(e));
    } finally {
      setApproving(false);
    }
  };

  const reject = async () => {
    if (!reason.trim()) { toast.error('Reason is required.'); return; }
    setRejecting(true);
    try {
      await signupRequestsApi.reject(req.id, reason.trim());
      setRejectOpen(false);
      const updated = await signupRequestsApi.get(req.id);
      setReq(updated.request);
      toast.success('Application rejected', 'Rejection email dispatched.');
    } catch (e) {
      toast.error('Could not reject', errMessage(e));
    } finally {
      setRejecting(false);
    }
  };

  return (
    <div>
      <Link to="/super/signup-requests" className="btn-ghost mb-3"><ArrowLeft size={14} /> Back to applications</Link>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge category={req.category}>{req.category}</Badge>
            {req.status === 'pending' && <Badge tone="warning">Pending</Badge>}
            {req.status === 'approved' && <Badge tone="success">Approved</Badge>}
            {req.status === 'rejected' && <Badge tone="danger">Rejected</Badge>}
          </div>
          <h1 className="mt-2 font-display text-4xl text-ink">{req.full_name}</h1>
          {req.business_name && <p className="text-inkm">{req.business_name}</p>}
        </div>
        {req.status === 'pending' && (
          <div className="flex gap-2">
            <Button variant="danger" onClick={() => setRejectOpen(true)}><X size={16} /> Reject</Button>
            <Button onClick={() => setApproveOpen(true)}><Check size={16} /> Approve</Button>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h3 className="font-display text-xl text-ink">Applicant</h3>
          <dl className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <div>
              <dt className="text-[10px] uppercase tracking-wider text-inkm">Email</dt>
              <dd className="mt-0.5 text-sm text-ink">{req.email}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wider text-inkm">Phone</dt>
              <dd className="mt-0.5 text-sm text-ink">{req.phone}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wider text-inkm">Suburb</dt>
              <dd className="mt-0.5 text-sm text-ink">{req.suburb}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase tracking-wider text-inkm">Submitted</dt>
              <dd className="mt-0.5 text-sm text-ink">{formatDateTime(req.created_at)}</dd>
            </div>
          </dl>
          <div className="mt-5">
            <dt className="text-[10px] uppercase tracking-wider text-inkm">Pitch</dt>
            <dd className="mt-1 whitespace-pre-wrap text-sm text-ink">{req.pitch}</dd>
          </div>
        </Card>
        <Card>
          <h3 className="font-display text-xl text-ink">Category payload</h3>
          <div className="mt-4">
            <PayloadDisplay payload={req.category_payload} />
          </div>
        </Card>
      </div>

      {req.status === 'rejected' && req.rejection_reason && (
        <Card className="mt-5 border-danger/30">
          <h3 className="font-display text-lg text-danger">Rejection reason</h3>
          <p className="mt-1 text-sm text-ink whitespace-pre-wrap">{req.rejection_reason}</p>
        </Card>
      )}

      {/* Approve modal */}
      <Modal
        open={approveOpen}
        onClose={() => !approving && setApproveOpen(false)}
        title="Approve application"
        footer={
          <>
            <Button variant="ghost" onClick={() => setApproveOpen(false)} disabled={approving}>Cancel</Button>
            <Button onClick={approve} loading={approving}>Approve & dispatch</Button>
          </>
        }
      >
        <p className="text-sm text-inkm">
          Approving will create the {req.category} profile, generate a temporary password,
          and dispatch credentials via the channels you pick below.
        </p>
        <div className="mt-4 space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={emailChannel}
              onChange={(e) => setEmailChannel(e.target.checked)}
              className="accent-brand"
            />
            <span className="text-sm text-ink">Email — {req.email}</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={whatsappChannel}
              onChange={(e) => setWhatsappChannel(e.target.checked)}
              className="accent-brand"
            />
            <span className="text-sm text-ink">WhatsApp deep-link — {req.phone}</span>
          </label>
        </div>
      </Modal>

      {/* Reject modal */}
      <Modal
        open={rejectOpen}
        onClose={() => !rejecting && setRejectOpen(false)}
        title="Reject application"
        footer={
          <>
            <Button variant="ghost" onClick={() => setRejectOpen(false)} disabled={rejecting}>Cancel</Button>
            <Button variant="danger" onClick={reject} loading={rejecting}>Reject & email</Button>
          </>
        }
      >
        <p className="text-sm text-inkm">
          The applicant will get an email with this reason. Be specific so they can re-apply.
        </p>
        <Textarea
          className="mt-3"
          rows={4}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. The pitch did not clearly describe the products being sold."
        />
      </Modal>

      {/* Temp password result */}
      <Modal
        open={Boolean(tempPwResult)}
        onClose={() => setTempPwResult(null)}
        title="Application approved"
        footer={
          <Button onClick={() => setTempPwResult(null)}>Done</Button>
        }
      >
        {tempPwResult && (
          <div>
            <p className="text-sm text-inkm">
              Credentials dispatched via <strong className="text-ink">{tempPwResult.channels.join(' + ')}</strong>.
            </p>
            <div className="mt-3 rounded-lg border border-brand/40 bg-brand/10 px-3 py-3">
              <div className="text-[10px] uppercase tracking-wider text-brand">Temporary password</div>
              <div className="mt-1 flex items-center justify-between gap-3">
                <code className="text-base text-ink">{tempPwResult.password}</code>
                <button
                  className="btn-secondary !py-1.5"
                  onClick={() => { navigator.clipboard?.writeText(tempPwResult.password); toast.success('Copied'); }}
                >
                  <Copy size={14} /> Copy
                </button>
              </div>
              <p className="mt-2 text-xs text-inkm">
                The applicant will be required to set a new password on first sign-in.
              </p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
