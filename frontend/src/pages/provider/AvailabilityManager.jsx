// /provider/availability — recurring weekly rules + one-off time blocks.
// Talks straight to BookingInterface's /api/provider/availability/*
// endpoints (this surface is BI-owned; Stage 4 just renders it).
import React, { useCallback, useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import {
  listRules, addRule, deleteRule, listBlocks, addBlock, deleteBlock,
} from '../../modules/booking_interface/api.js';
import { Button } from '../../components/ui/Button.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { errMessage } from '../../api/client.js';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function AvailabilityManager() {
  const toast = useToast();
  const [rules, setRules] = useState(null);
  const [blocks, setBlocks] = useState(null);
  const [ruleForm, setRuleForm] = useState({ weekday: 0, start_time: '08:00', end_time: '17:00' });
  const [blockForm, setBlockForm] = useState({ start_at: '', end_at: '', reason: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    listRules().then(setRules).catch(() => setRules([]));
    listBlocks().then(setBlocks).catch(() => setBlocks([]));
  }, []);
  useEffect(load, [load]);

  const submitRule = async () => {
    setBusy(true);
    try {
      await addRule({ ...ruleForm, weekday: Number(ruleForm.weekday) });
      toast.success('Weekly hours added.');
      load();
    } catch (err) { toast.error(errMessage(err)); }
    finally { setBusy(false); }
  };

  const submitBlock = async () => {
    setBusy(true);
    try {
      await addBlock({
        start_at: new Date(blockForm.start_at).toISOString(),
        end_at: new Date(blockForm.end_at).toISOString(),
        reason: blockForm.reason,
      });
      toast.success('Time blocked out.');
      setBlockForm({ start_at: '', end_at: '', reason: '' });
      load();
    } catch (err) { toast.error(errMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">Availability</h1>
        <p className="mt-1 text-sm text-inkm">
          Your weekly open hours, minus one-off blocks, minus confirmed bookings —
          that's what buyers can request. Times are in your local (Harare) time.
        </p>
      </div>

      <section className="card space-y-4 p-5">
        <h2 className="font-display text-lg text-ink">Weekly hours</h2>
        {rules === null && <p className="text-sm text-inkm">Loading…</p>}
        {rules && rules.length === 0 && (
          <p className="text-sm text-warning">
            No open hours yet — buyers can't request bookings until you add some.
          </p>
        )}
        <ul className="divide-y divide-bordr">
          {(rules || []).map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <span className="text-ink">
                {DAYS[r.weekday]} · {r.start_time} – {r.end_time}
              </span>
              <Button variant="ghost" onClick={async () => {
                try { await deleteRule(r.id); load(); }
                catch (err) { toast.error(errMessage(err)); }
              }}>
                <Trash2 size={14} /> Remove
              </Button>
            </li>
          ))}
        </ul>
        <div className="grid items-end gap-3 sm:grid-cols-[1fr,auto,auto,auto]">
          <Select label="Day" value={ruleForm.weekday}
                  onChange={(e) => setRuleForm({ ...ruleForm, weekday: e.target.value })}>
            {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
          </Select>
          <Input label="From" type="time" value={ruleForm.start_time}
                 onChange={(e) => setRuleForm({ ...ruleForm, start_time: e.target.value })} />
          <Input label="To" type="time" value={ruleForm.end_time}
                 onChange={(e) => setRuleForm({ ...ruleForm, end_time: e.target.value })} />
          <Button loading={busy} onClick={submitRule}><Plus size={15} /> Add</Button>
        </div>
      </section>

      <section className="card space-y-4 p-5">
        <h2 className="font-display text-lg text-ink">Blocked-out time</h2>
        <p className="text-sm text-inkm">One-off unavailability — leave, supplier runs, family days.</p>
        <ul className="divide-y divide-bordr">
          {(blocks || []).map((b) => (
            <li key={b.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <span className="text-ink">
                {new Date(b.start_at).toLocaleString()} → {new Date(b.end_at).toLocaleString()}
                {b.reason && <span className="ml-2 text-inkm">— {b.reason}</span>}
              </span>
              <Button variant="ghost" onClick={async () => {
                try { await deleteBlock(b.id); load(); }
                catch (err) { toast.error(errMessage(err)); }
              }}>
                <Trash2 size={14} /> Remove
              </Button>
            </li>
          ))}
        </ul>
        <div className="grid items-end gap-3 sm:grid-cols-[1fr,1fr,1fr,auto]">
          <Input label="From" type="datetime-local" value={blockForm.start_at}
                 onChange={(e) => setBlockForm({ ...blockForm, start_at: e.target.value })} />
          <Input label="To" type="datetime-local" value={blockForm.end_at}
                 onChange={(e) => setBlockForm({ ...blockForm, end_at: e.target.value })} />
          <Input label="Reason (optional)" value={blockForm.reason}
                 onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })} />
          <Button loading={busy} disabled={!blockForm.start_at || !blockForm.end_at}
                  onClick={submitBlock}>
            <Plus size={15} /> Block
          </Button>
        </div>
      </section>
    </div>
  );
}
