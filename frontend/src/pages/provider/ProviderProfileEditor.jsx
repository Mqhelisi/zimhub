// /provider/profile — edits the merged profile: public identity (display
// name, trade, bio, photo, suburbs served) + booking settings (cancel
// cutoff, response window, timezone). One PUT to /api/provider/profile.
import React, { useEffect, useState } from 'react';
import { Upload } from 'lucide-react';
import {
  getProviderProfile, updateProviderProfile, uploadProviderImage,
} from '../../components/services/api.js';
import { Button } from '../../components/ui/Button.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { BULAWAYO_SUBURBS } from '../../components/ui/SuburbSelect.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { errMessage } from '../../api/client.js';

const TRADES = ['Plumber', 'Electrician', 'Hairdresser', 'Driver', 'Maid',
  'Mechanic', 'Tutor', 'Photographer-for-hire', 'Other'];

export default function ProviderProfileEditor() {
  const toast = useToast();
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    getProviderProfile().then((p) => setForm({
      display_name: p.display_name || '',
      trade: p.trade || 'Other',
      bio: p.bio || '',
      photo_url: p.photo_url || '',
      suburbs_served: p.suburbs_served || [],
      cancel_cutoff_hours: p.cancel_cutoff_hours ?? 0,
      response_hours: p.response_hours ?? '',
      slug: p.slug,
    })).catch(() => setForm(false));
  }, []);

  if (form === false) return <div className="card p-8 text-center text-inkm">Could not load your profile.</div>;
  if (!form) return <p className="text-sm text-inkm">Loading…</p>;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async () => {
    setBusy(true);
    try {
      await updateProviderProfile({
        display_name: form.display_name,
        trade: form.trade,
        bio: form.bio,
        photo_url: form.photo_url || null,
        suburbs_served: form.suburbs_served,
        cancel_cutoff_hours: Number(form.cancel_cutoff_hours) || 0,
        response_hours: form.response_hours === '' ? null : Number(form.response_hours),
      });
      toast.success('Profile saved.');
    } catch (err) { toast.error(errMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div>
        <h1 className="heading-accent font-display text-2xl text-ink">Profile</h1>
        {form.slug && (
          <p className="mt-1 text-sm text-inkm">
            Public page: <a href={`/services/providers/${form.slug}`} className="text-brand">
              /services/providers/{form.slug}
            </a>
          </p>
        )}
      </div>
      <div className="card space-y-4 p-5">
        <Input label="Display name" value={form.display_name}
               onChange={(e) => set('display_name', e.target.value)} />
        <Select label="Trade" value={form.trade} onChange={(e) => set('trade', e.target.value)}>
          {TRADES.map((t) => <option key={t} value={t}>{t}</option>)}
        </Select>
        <Textarea label="Bio" rows={3} value={form.bio}
                  onChange={(e) => set('bio', e.target.value)}
                  placeholder="What you do, how you work, what makes you reliable…" />
        <div>
          <label className="mb-1.5 block text-sm text-inkm">Photo</label>
          <div className="flex items-center gap-3">
            {form.photo_url && (
              <img src={form.photo_url} alt="" className="h-14 w-14 rounded-xl border border-bordr object-cover" />
            )}
            <label className="btn-secondary cursor-pointer">
              <Upload size={15} /> {uploading ? 'Uploading…' : 'Upload'}
              <input type="file" accept="image/*" className="hidden"
                     onChange={async (e) => {
                       const file = e.target.files?.[0];
                       if (!file) return;
                       setUploading(true);
                       try { set('photo_url', await uploadProviderImage(file)); }
                       catch (err) { toast.error(errMessage(err)); }
                       finally { setUploading(false); }
                     }} />
            </label>
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-sm text-inkm">Suburbs served</label>
          <div className="flex flex-wrap gap-2">
            {BULAWAYO_SUBURBS.map((s) => {
              const on = form.suburbs_served.includes(s);
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => set('suburbs_served', on
                    ? form.suburbs_served.filter((x) => x !== s)
                    : [...form.suburbs_served, s])}
                  className={`rounded-full border px-3 py-1 text-xs transition ${
                    on
                      ? 'border-[rgb(var(--section-accent))] bg-[rgb(var(--section-accent)/0.15)] text-ink'
                      : 'border-bordr bg-bgs text-inkm hover:text-ink'
                  }`}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Cancel cutoff (hours before start)" type="number" min="0"
                 value={form.cancel_cutoff_hours}
                 onChange={(e) => set('cancel_cutoff_hours', e.target.value)} />
          <Input label="Response window (hours, optional)" type="number" min="1"
                 value={form.response_hours}
                 onChange={(e) => set('response_hours', e.target.value)}
                 placeholder="Blank = until start time" />
        </div>
        <div className="flex justify-end">
          <Button loading={busy} onClick={save}>Save profile</Button>
        </div>
      </div>
    </div>
  );
}
