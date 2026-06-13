import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Copy, KeyRound, Ban, Power } from 'lucide-react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Badge } from '../../components/ui/Badge.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Modal } from '../../components/ui/Modal.jsx';
import { superUsersApi } from '../../api/superUsers.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { formatDateTime } from '../../utils/time.js';
import { errMessage } from '../../api/client.js';

const CAPS = [
  { key: 'is_salesman', label: 'Salesman', category: 'salesman' },
  { key: 'is_promoter', label: 'Promoter', category: 'promoter' },
  { key: 'is_provider', label: 'Provider', category: 'provider' },
  { key: 'is_creator',  label: 'Creator',  category: 'creator' },
  { key: 'is_super_admin', label: 'Super admin', category: null },
];

function ProfileSnapshot({ category, profile }) {
  if (!profile) return null;
  return (
    <Card>
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg text-ink capitalize">{category} profile</h3>
        <Badge category={category}>{category}</Badge>
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {Object.entries(profile).map(([k, v]) => (
          k === 'user_id' ? null : (
            <div key={k}>
              <dt className="text-[10px] uppercase tracking-wider text-inkm">{k.replace(/_/g, ' ')}</dt>
              <dd className="mt-0.5 text-sm text-ink break-words">
                {Array.isArray(v) ? (v.length ? v.join(', ') : '—') : (typeof v === 'object' && v !== null ? JSON.stringify(v) : (v ?? '—'))}
              </dd>
            </div>
          )
        ))}
      </dl>
    </Card>
  );
}

export default function UserDetail() {
  const { id } = useParams();
  const toast = useToast();
  const { user: signedInUser } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Confirm-toggle modal
  const [pending, setPending] = useState(null); // { key, label, newValue }
  // Reset-password modal
  const [resetOpen, setResetOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState(true);
  const [resetWhatsapp, setResetWhatsapp] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [resetResult, setResetResult] = useState(null);

  const refresh = () => {
    setLoading(true);
    superUsersApi.get(id)
      .then((d) => { setData(d); setError(''); })
      .catch((e) => setError(e?.response?.data?.message || 'User not found.'))
      .finally(() => setLoading(false));
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [id]);

  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>;
  if (error) return <div className="text-danger">{error}</div>;
  if (!data) return null;

  const { user, capabilities, profiles } = data;
  const isSelf = signedInUser?.id === user.id;

  const confirmToggle = async () => {
    if (!pending) return;
    try {
      await superUsersApi.patchCapabilities(user.id, { [pending.key]: pending.newValue });
      setPending(null);
      toast.success(
        `${pending.label} ${pending.newValue ? 'enabled' : 'disabled'}`,
        pending.newValue && pending.category ? `${pending.category} profile shell ensured.` : null
      );
      refresh();
    } catch (e) {
      toast.error('Could not update capability', errMessage(e));
    }
  };

  const toggleSuspend = async () => {
    try {
      if (user.status === 'suspended') {
        await superUsersApi.unsuspend(user.id);
        toast.success('User unsuspended');
      } else {
        await superUsersApi.suspend(user.id, null);
        toast.success('User suspended');
      }
      refresh();
    } catch (e) {
      toast.error('Could not update status', errMessage(e));
    }
  };

  const resetPassword = async () => {
    const channels = [];
    if (resetEmail) channels.push('email');
    if (resetWhatsapp) channels.push('whatsapp');
    if (channels.length === 0) { toast.error('Pick at least one delivery channel.'); return; }
    setResetting(true);
    try {
      const r = await superUsersApi.resetPassword(user.id, channels);
      setResetOpen(false);
      setResetResult({ password: r.temp_password, channels: r.delivery_channels });
      toast.success('Password reset', `Dispatched via ${r.delivery_channels.join(' + ')}`);
    } catch (e) {
      toast.error('Could not reset password', errMessage(e));
    } finally {
      setResetting(false);
    }
  };

  return (
    <div>
      <Link to="/super/users" className="btn-ghost mb-3"><ArrowLeft size={14} /> Back to users</Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl text-ink">{user.name}</h1>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-inkm">
            <span>{user.email}</span>
            <span className="opacity-60">·</span>
            <span>{user.phone}</span>
            {user.suburb && <><span className="opacity-60">·</span><span>{user.suburb}</span></>}
            {user.status === 'suspended' && <Badge tone="danger">Suspended</Badge>}
          </div>
          <div className="mt-1 text-xs text-inkm">Joined {formatDateTime(user.created_at)}</div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setResetOpen(true)}>
            <KeyRound size={16} /> Reset password
          </Button>
          {!isSelf && (
            <Button
              variant={user.status === 'suspended' ? 'secondary' : 'danger'}
              onClick={toggleSuspend}
            >
              {user.status === 'suspended' ? <><Power size={16} /> Unsuspend</> : <><Ban size={16} /> Suspend</>}
            </Button>
          )}
        </div>
      </div>

      <Card className="mt-5">
        <h3 className="font-display text-lg text-ink">Capabilities</h3>
        <p className="mt-1 text-xs text-inkm">
          Turning a seller capability ON creates its profile shell. Turning OFF leaves the profile in place
          (soft-disable).
        </p>
        <div className="mt-4 space-y-2">
          {CAPS.map((cap) => {
            const isOn = Boolean(capabilities?.[cap.key]);
            const disabled = isSelf && cap.key === 'is_super_admin';
            return (
              <div key={cap.key} className="flex items-center justify-between rounded-lg border border-bordr bg-bgs2/60 px-3 py-2.5">
                <div>
                  <div className="text-sm text-ink">{cap.label}</div>
                  <div className="text-xs text-inkm">
                    {isOn ? 'Active' : 'Inactive'}{cap.category ? ` · ${cap.category}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => !disabled && setPending({
                    key: cap.key, label: cap.label, category: cap.category, newValue: !isOn,
                  })}
                  disabled={disabled}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    isOn ? 'bg-brand' : 'bg-bgs2 border border-bordr'
                  } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                  aria-label={`Toggle ${cap.label}`}
                >
                  <span className={`inline-block h-5 w-5 transform rounded-full bg-ink transition ${
                    isOn ? 'translate-x-5' : 'translate-x-0.5'
                  }`} />
                </button>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <ProfileSnapshot category="salesman" profile={profiles.salesman} />
        <ProfileSnapshot category="promoter" profile={profiles.promoter} />
        <ProfileSnapshot category="provider" profile={profiles.provider} />
        <ProfileSnapshot category="creator" profile={profiles.creator} />
      </div>

      {/* Confirm-toggle modal */}
      <Modal
        open={Boolean(pending)}
        onClose={() => setPending(null)}
        title={pending ? `${pending.newValue ? 'Enable' : 'Disable'} ${pending.label}?` : ''}
        footer={
          <>
            <Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
            <Button onClick={confirmToggle}>Confirm</Button>
          </>
        }
      >
        {pending && (
          <p className="text-sm text-inkm">
            {pending.newValue
              ? `This will turn on the ${pending.label} capability${pending.category ? ` and create the ${pending.category} profile shell if it doesn't exist` : ''}.`
              : `This will turn off the ${pending.label} capability. The profile (if any) stays in place — flip the toggle back on to restore access.`
            }
          </p>
        )}
      </Modal>

      {/* Reset password modal */}
      <Modal
        open={resetOpen}
        onClose={() => !resetting && setResetOpen(false)}
        title="Reset user password"
        footer={
          <>
            <Button variant="ghost" onClick={() => setResetOpen(false)} disabled={resetting}>Cancel</Button>
            <Button onClick={resetPassword} loading={resetting}>Reset & dispatch</Button>
          </>
        }
      >
        <p className="text-sm text-inkm">
          A new temporary password will be generated. The user will be required to change it on next sign-in.
        </p>
        <div className="mt-4 space-y-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={resetEmail} onChange={(e) => setResetEmail(e.target.checked)} className="accent-brand" />
            <span className="text-sm text-ink">Email — {user.email}</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={resetWhatsapp} onChange={(e) => setResetWhatsapp(e.target.checked)} className="accent-brand" />
            <span className="text-sm text-ink">WhatsApp — {user.phone}</span>
          </label>
        </div>
      </Modal>

      {/* Temp password reveal */}
      <Modal
        open={Boolean(resetResult)}
        onClose={() => setResetResult(null)}
        title="Password reset"
        footer={<Button onClick={() => setResetResult(null)}>Done</Button>}
      >
        {resetResult && (
          <div>
            <p className="text-sm text-inkm">
              Dispatched via <strong className="text-ink">{resetResult.channels.join(' + ')}</strong>.
            </p>
            <div className="mt-3 rounded-lg border border-brand/40 bg-brand/10 px-3 py-3">
              <div className="text-[10px] uppercase tracking-wider text-brand">Temporary password</div>
              <div className="mt-1 flex items-center justify-between gap-3">
                <code className="text-base text-ink">{resetResult.password}</code>
                <button
                  className="btn-secondary !py-1.5"
                  onClick={() => { navigator.clipboard?.writeText(resetResult.password); toast.success('Copied'); }}
                >
                  <Copy size={14} /> Copy
                </button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
