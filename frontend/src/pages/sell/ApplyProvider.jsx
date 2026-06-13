import React, { useState } from 'react';
import { useFormContext } from 'react-hook-form';
import { ApplyShared } from './ApplyShared.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { X } from 'lucide-react';
import { BULAWAYO_SUBURBS } from '../../components/ui/SuburbSelect.jsx';

function ProviderFields() {
  const { register, formState: { errors }, setValue } = useFormContext();
  const [areas, setAreas] = useState([]);
  const [custom, setCustom] = useState('');

  React.useEffect(() => { setValue('service_areas', areas); }, [areas, setValue]);

  const toggle = (a) => setAreas((prev) => prev.includes(a) ? prev.filter(x => x !== a) : [...prev, a]);
  const addCustom = () => {
    const v = custom.trim();
    if (!v) return;
    if (!areas.includes(v)) setAreas([...areas, v]);
    setCustom('');
  };

  return (
    <>
      <Input
        label="Trade"
        placeholder="e.g. Plumber, Electrician, Hairdresser"
        error={errors.trade?.message}
        {...register('trade', { required: 'Required' })}
      />
      <Input
        label="Years of experience"
        type="number"
        min={0}
        error={errors.years_experience?.message}
        {...register('years_experience', { required: 'Required', valueAsNumber: true })}
      />
      <Select
        label="Pricing unit preference"
        error={errors.pricing_unit_preference?.message}
        {...register('pricing_unit_preference', { required: 'Required' })}
      >
        <option value="">Choose one</option>
        <option value="per_job">Per job</option>
        <option value="per_hour">Per hour</option>
        <option value="per_day">Per day</option>
        <option value="quote_only">Quote on request</option>
      </Select>
      <div>
        <label className="label">Service areas (Bulawayo suburbs)</label>
        <div className="flex flex-wrap gap-1.5">
          {BULAWAYO_SUBURBS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => toggle(s)}
              className={`pill cursor-pointer transition ${
                areas.includes(s) ? 'border-services/60 bg-services/15 text-services' : ''
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addCustom(); } }}
            placeholder="Add another suburb…"
            className="input-base"
          />
          <button type="button" onClick={addCustom} className="btn-secondary">Add</button>
        </div>
        {areas.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {areas.map((c) => (
              <span key={c} className="pill border-services/60 bg-services/15 text-services">
                {c}
                <button type="button" onClick={() => toggle(c)} className="ml-1 opacity-70 hover:opacity-100">
                  <X size={11} />
                </button>
              </span>
            ))}
          </div>
        )}
        {errors.service_areas?.message && (
          <p className="mt-1 text-xs text-danger">{errors.service_areas.message}</p>
        )}
        <input type="hidden" {...register('service_areas', {
          validate: () => areas.length > 0 || 'Pick at least one suburb',
        })} />
      </div>
    </>
  );
}

export default function ApplyProvider() {
  return (
    <ApplyShared
      category="provider"
      title="Apply as a Service Provider"
      lede="Take bookings on ZimHub Services — any trade, any pricing model."
      businessNameLabel="Business name (optional)"
      buildPayload={(d) => ({
        trade: d.trade,
        years_experience: d.years_experience,
        service_areas: d.service_areas || [],
        pricing_unit_preference: d.pricing_unit_preference,
      })}
    >
      <ProviderFields />
    </ApplyShared>
  );
}
