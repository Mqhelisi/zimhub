import React, { useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { ApplyShared } from './ApplyShared.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { X } from 'lucide-react';

const CREATOR_TYPES = [
  'Musician', 'Producer', 'Photographer', 'Videographer', 'Visual artist',
  'Writer', 'Poet', 'Designer', 'DJ', 'Fashion designer', 'Other',
];

function TagPicker({ name, label, accentClass = 'border-creators/60 bg-creators/15 text-creators', presets = [], placeholder }) {
  const { register, formState: { errors }, setValue } = useFormContext();
  const [items, setItems] = useState([]);
  const [custom, setCustom] = useState('');

  React.useEffect(() => { setValue(name, items); }, [items, name, setValue]);

  const toggle = (v) => setItems((prev) => prev.includes(v) ? prev.filter(x => x !== v) : [...prev, v]);
  const addCustom = () => {
    const v = custom.trim();
    if (!v) return;
    if (!items.includes(v)) setItems([...items, v]);
    setCustom('');
  };

  return (
    <div>
      <label className="label">{label}</label>
      {presets.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {presets.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => toggle(p)}
              className={`pill cursor-pointer transition ${items.includes(p) ? accentClass : ''}`}
            >
              {p}
            </button>
          ))}
        </div>
      )}
      <div className="mt-2 flex gap-2">
        <input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustom(); } }}
          placeholder={placeholder || 'Add…'}
          className="input-base"
        />
        <button type="button" onClick={addCustom} className="btn-secondary">Add</button>
      </div>
      {items.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {items.map((c) => (
            <span key={c} className={`pill ${accentClass}`}>
              {c}
              <button type="button" onClick={() => toggle(c)} className="ml-1 opacity-70 hover:opacity-100">
                <X size={11} />
              </button>
            </span>
          ))}
        </div>
      )}
      {errors[name]?.message && <p className="mt-1 text-xs text-danger">{errors[name].message}</p>}
      <input type="hidden" {...register(name)} />
    </div>
  );
}

function CreatorFields() {
  const { register, formState: { errors }, setValue } = useFormContext();
  const [urls, setUrls] = useState([]);
  const [urlInput, setUrlInput] = useState('');

  React.useEffect(() => { setValue('sample_work_urls', urls); }, [urls, setValue]);

  const addUrl = () => {
    const v = urlInput.trim();
    if (!v) return;
    if (!urls.includes(v)) setUrls([...urls, v]);
    setUrlInput('');
  };
  const removeUrl = (v) => setUrls((prev) => prev.filter(x => x !== v));

  return (
    <>
      <TagPicker
        name="creator_types"
        label="Creator types"
        accentClass="border-creators/60 bg-creators/15 text-creators"
        presets={CREATOR_TYPES}
        placeholder="Add a custom type"
      />
      <TagPicker
        name="discipline_tags"
        label="Discipline tags (genre, style, etc.)"
        accentClass="border-creators/60 bg-creators/15 text-creators"
        presets={[]}
        placeholder="e.g. afro-soul, jazz, portrait, documentary"
      />
      <div>
        <label className="label">Sample work URLs</label>
        <div className="flex gap-2">
          <input
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addUrl(); } }}
            placeholder="https://…"
            className="input-base"
          />
          <button type="button" onClick={addUrl} className="btn-secondary">Add</button>
        </div>
        {urls.length > 0 && (
          <ul className="mt-2 space-y-1">
            {urls.map((u) => (
              <li key={u} className="flex items-center justify-between rounded-md border border-bordr bg-bgs2 px-3 py-1.5 text-sm">
                <span className="truncate text-ink">{u}</span>
                <button type="button" onClick={() => removeUrl(u)} className="text-inkm hover:text-danger">
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <input type="hidden" {...register('sample_work_urls')} />
      </div>
    </>
  );
}

export default function ApplyCreator() {
  return (
    <ApplyShared
      category="creator"
      title="Apply as a Creator"
      lede="A single home for your music, photography, art, or writing — on ZimHub Creators."
      businessNameLabel="Stage / display name (optional)"
      buildPayload={(d) => ({
        creator_types: d.creator_types || [],
        sample_work_urls: d.sample_work_urls || [],
        discipline_tags: d.discipline_tags || [],
      })}
    >
      <CreatorFields />
    </ApplyShared>
  );
}
