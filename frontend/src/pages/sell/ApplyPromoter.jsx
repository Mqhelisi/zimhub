import React, { useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { ApplyShared } from './ApplyShared.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { X } from 'lucide-react';

const PRESET_CATEGORIES = [
  'Live music', 'Festival', 'Sundowner', 'Cultural night', 'Comedy',
  'Sport', 'Conference', 'Workshop', 'Family', 'Outdoor',
];

function PromoterFields() {
  const { register, formState: { errors }, setValue, watch } = useFormContext();
  const [pick, setPick] = useState([]);
  const [custom, setCustom] = useState('');

  // Sync into RHF as a hidden field
  React.useEffect(() => { setValue('event_categories', pick); }, [pick, setValue]);

  const toggle = (c) => setPick((prev) => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);
  const addCustom = () => {
    const v = custom.trim();
    if (!v) return;
    if (!pick.includes(v)) setPick([...pick, v]);
    setCustom('');
  };

  const eventCatsError = errors.event_categories?.message;

  return (
    <>
      <Input
        label="Organisation name (if any)"
        error={errors.organisation_name?.message}
        {...register('organisation_name')}
      />
      <Textarea
        label="Past events (optional)"
        rows={2}
        placeholder="Briefly list the events you've run before."
        {...register('past_events')}
      />
      <Input
        label="Sample poster URL (optional)"
        placeholder="https://…"
        {...register('sample_poster_url')}
      />
      <div>
        <label className="label">Event categories</label>
        <div className="flex flex-wrap gap-1.5">
          {PRESET_CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => toggle(c)}
              className={`pill cursor-pointer transition ${
                pick.includes(c) ? 'border-events/60 bg-events/15 text-events' : ''
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustom(); } }}
            placeholder="Add another…"
            className="input-base"
          />
          <button type="button" onClick={addCustom} className="btn-secondary">Add</button>
        </div>
        {pick.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {pick.map((c) => (
              <span key={c} className="pill border-events/60 bg-events/15 text-events">
                {c}
                <button type="button" onClick={() => toggle(c)} className="ml-1 opacity-70 hover:opacity-100">
                  <X size={11} />
                </button>
              </span>
            ))}
          </div>
        )}
        {eventCatsError && <p className="mt-1 text-xs text-danger">{eventCatsError}</p>}
        <input type="hidden" {...register('event_categories', {
          validate: () => pick.length > 0 || 'Pick at least one category',
        })} />
      </div>
    </>
  );
}

export default function ApplyPromoter() {
  return (
    <ApplyShared
      category="promoter"
      title="Apply as a Promoter"
      lede="Run events on ZimHub Events — QR-coded tickets, attendee lists, and a public event page."
      businessNameLabel="Organisation name (optional)"
      buildPayload={(d) => ({
        organisation_name: d.organisation_name || null,
        past_events: d.past_events || null,
        sample_poster_url: d.sample_poster_url || null,
        event_categories: d.event_categories || [],
      })}
    >
      <PromoterFields />
    </ApplyShared>
  );
}
