import React, { useEffect, useState } from 'react';
import { Card, Spinner } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { systemApi } from '../../api/system.js';
import { useToast } from '../../components/ui/Toast.jsx';
import { useDemoMode } from '../../contexts/DemoModeContext.jsx';
import { errMessage } from '../../api/client.js';

const FIELDS = [
  { key: 'DEMO_MODE', label: 'DEMO MODE', type: 'bool',
    hint: 'When on, the yellow banner is visible across all pages.' },
  { key: 'EVENT_MODERATION', label: 'Event moderation', type: 'bool',
    hint: 'Will be wired by the Events module in Stage 3.' },
  { key: 'HOLD_HOURS', label: 'Hold hours', type: 'int',
    hint: 'How long a buyer hold lasts before auto-release. Stage 2.' },
  { key: 'SETTLE_HOURS', label: 'Settle hours', type: 'int',
    hint: 'How long after delivery payments settle to sellers. Stage 2.' },
  { key: 'RESPONSE_HOURS', label: 'Response hours (bookings)', type: 'int',
    hint: 'Empty = expires at the booking start time. Stage 4.' },
  { key: 'CANCEL_CUTOFF_HOURS', label: 'Cancel cutoff hours', type: 'int',
    hint: 'How close to start time a booking can be cancelled. Stage 4.' },
  { key: 'DEFAULT_CURRENCY', label: 'Default currency', type: 'string' },
  { key: 'DEFAULT_TIMEZONE', label: 'Default time zone', type: 'string' },
];

export default function SystemConfig() {
  const toast = useToast();
  const { refresh: refreshDemo } = useDemoMode();
  const [config, setConfig] = useState(null);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    systemApi.getConfig()
      .then(({ config }) => { setConfig(config); setDraft(config); })
      .catch((e) => setError(e?.response?.data?.message || 'Could not load config.'));
  }, []);

  const updateField = (key, value) => setDraft((d) => ({ ...d, [key]: value }));
  const dirty = config && JSON.stringify(config) !== JSON.stringify(draft);

  const save = async () => {
    setSaving(true);
    try {
      // Only send keys the user actually changed.
      const changes = {};
      for (const f of FIELDS) {
        if (config[f.key] !== draft[f.key]) changes[f.key] = draft[f.key];
      }
      const { config: next } = await systemApi.putConfig(changes);
      setConfig(next);
      setDraft(next);
      toast.success('Config saved');
      refreshDemo(); // banner reflects DEMO_MODE change immediately
    } catch (e) {
      toast.error('Could not save config', errMessage(e));
    } finally {
      setSaving(false);
    }
  };

  if (error) return <div className="text-danger">{error}</div>;
  if (!config) return <div className="flex justify-center py-10"><Spinner /></div>;

  return (
    <div>
      <h1 className="font-display text-4xl text-ink">System config</h1>
      <p className="mt-1 text-sm text-inkm">Runtime-tunable settings. Stage 2+ modules read from here.</p>

      <Card className="mt-6 space-y-5">
        {FIELDS.map((f) => (
          <div key={f.key} className="grid items-center gap-3 sm:grid-cols-[260px_1fr] border-b border-bordr pb-4 last:border-b-0 last:pb-0">
            <div>
              <div className="text-sm font-semibold text-ink">{f.label}</div>
              <div className="text-[11px] text-inkm font-mono">{f.key}</div>
              {f.hint && <div className="mt-1 text-xs text-inkm">{f.hint}</div>}
            </div>
            <div>
              {f.type === 'bool' ? (
                <button
                  onClick={() => updateField(f.key, !draft[f.key])}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    draft[f.key] ? 'bg-brand' : 'bg-bgs2 border border-bordr'
                  }`}
                >
                  <span className={`inline-block h-5 w-5 transform rounded-full bg-ink transition ${
                    draft[f.key] ? 'translate-x-5' : 'translate-x-0.5'
                  }`} />
                </button>
              ) : f.type === 'int' ? (
                <Input
                  type="number"
                  value={draft[f.key] === null || draft[f.key] === undefined ? '' : draft[f.key]}
                  onChange={(e) => updateField(f.key, e.target.value === '' ? null : Number(e.target.value))}
                  className="max-w-[12rem]"
                />
              ) : (
                <Input
                  value={draft[f.key] ?? ''}
                  onChange={(e) => updateField(f.key, e.target.value)}
                  className="max-w-sm"
                />
              )}
            </div>
          </div>
        ))}
      </Card>

      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={() => setDraft(config)} disabled={!dirty}>Discard</Button>
        <Button onClick={save} loading={saving} disabled={!dirty}>Save changes</Button>
      </div>
    </div>
  );
}
