// /provider/services + /provider/services/new|:id — catalog list and the
// service editor (react-hook-form + zod, matching the Stage 2/3 editor
// pattern). Delete = soft archive; per_km gets the "billed by distance" hint.
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Archive, Pencil } from 'lucide-react';
import {
  listMyServices, getMyService, createService, updateService, archiveService,
} from '../../components/services/api.js';
import { PricingUnitChip } from '../../components/services/ServicesSectionLayout.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { Select } from '../../components/ui/Select.jsx';
import { useToast } from '../../components/ui/Toast.jsx';
import { errMessage, errFieldErrors } from '../../api/client.js';

// ---------------------------------------------------------------------------
export function ServicesCatalog() {
  const [services, setServices] = useState(null);
  const [showArchived, setShowArchived] = useState(false);
  const toast = useToast();

  const load = useCallback(() => {
    listMyServices().then(setServices).catch(() => setServices([]));
  }, []);
  useEffect(load, [load]);

  const visible = (services || []).filter(
    (s) => showArchived || s.status === 'active',
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="heading-accent font-display text-2xl text-ink">My services</h1>
          <p className="mt-1 text-sm text-inkm">Each service is bookable against your one calendar.</p>
        </div>
        <Link to="/provider/services/new" className="btn-primary"><Plus size={16} /> New service</Link>
      </div>
      <label className="flex items-center gap-2 text-sm text-inkm">
        <input type="checkbox" checked={showArchived}
               onChange={(e) => setShowArchived(e.target.checked)} />
        Show archived
      </label>
      {services === null && <p className="text-sm text-inkm">Loading…</p>}
      {services && visible.length === 0 && (
        <div className="card p-8 text-center text-inkm">
          No services yet — add your first to appear in the directory.
        </div>
      )}
      <div className="space-y-3">
        {visible.map((s) => (
          <div key={s.id} className={`card p-4 ${s.status === 'archived' ? 'opacity-60' : ''}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="truncate font-medium text-ink">{s.name}</h3>
                  {s.status === 'archived' && (
                    <span className="rounded-full border border-bordr bg-bgs2 px-2 py-0.5 text-[10.5px] uppercase tracking-wider text-inkm">
                      Archived
                    </span>
                  )}
                </div>
                <p className="mt-1 line-clamp-1 text-sm text-inkm">{s.description}</p>
                <div className="mt-2 flex items-center gap-2">
                  <PricingUnitChip unit={s.pricing_unit} rate={s.rate_usd} />
                  {s.default_duration_minutes && (
                    <span className="text-xs text-inkm">~{s.default_duration_minutes} min</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Link to={`/provider/services/${s.id}`} className="btn-secondary">
                  <Pencil size={14} /> Edit
                </Link>
                {s.status === 'active' && (
                  <Button
                    variant="ghost"
                    onClick={async () => {
                      try {
                        await archiveService(s.id);
                        toast.success('Service archived — past bookings keep their record.');
                        load();
                      } catch (err) { toast.error(errMessage(err)); }
                    }}
                  >
                    <Archive size={14} /> Archive
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
const schema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(200),
  description: z.string().trim().min(1, 'Description is required'),
  pricing_unit: z.enum(['flat', 'per_hour', 'per_day', 'per_km']),
  rate_usd: z.coerce.number({ invalid_type_error: 'Rate must be a number' })
    .min(0, 'Rate must be at least $0'),
  default_duration_minutes: z.union([
    z.literal('').transform(() => null),
    z.coerce.number().int().positive('Duration must be positive'),
  ]).nullable().optional(),
});

export function ServiceEditor() {
  const { serviceId } = useParams();
  const isNew = !serviceId || serviceId === 'new';
  const navigate = useNavigate();
  const toast = useToast();
  const [loaded, setLoaded] = useState(isNew);

  const {
    register, handleSubmit, reset, watch, setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { pricing_unit: 'flat', default_duration_minutes: '' },
  });
  const unit = watch('pricing_unit');

  useEffect(() => {
    if (isNew) return;
    getMyService(serviceId).then((s) => {
      reset({
        name: s.name, description: s.description, pricing_unit: s.pricing_unit,
        rate_usd: s.rate_usd, default_duration_minutes: s.default_duration_minutes ?? '',
      });
      setLoaded(true);
    }).catch(() => { toast.error('Service not found.'); navigate('/provider/services'); });
  }, [isNew, serviceId, reset, navigate, toast]);

  const onSubmit = async (values) => {
    const payload = { ...values, default_duration_minutes: values.default_duration_minutes || null };
    try {
      if (isNew) await createService(payload);
      else await updateService(serviceId, payload);
      toast.success(isNew ? 'Service created.' : 'Service updated.');
      navigate('/provider/services');
    } catch (err) {
      const fields = errFieldErrors(err);
      Object.entries(fields || {}).forEach(([k, v]) => setError(k, { message: v }));
      toast.error(errMessage(err));
    }
  };

  if (!loaded) return <p className="text-sm text-inkm">Loading…</p>;

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="heading-accent font-display text-2xl text-ink">
        {isNew ? 'New service' : 'Edit service'}
      </h1>
      <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4 p-5">
        <Input label="Name" error={errors.name?.message} {...register('name')} />
        <Textarea label="Description" rows={3}
                  error={errors.description?.message} {...register('description')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label="Pricing unit" error={errors.pricing_unit?.message}
                  {...register('pricing_unit')}>
            <option value="flat">Flat rate</option>
            <option value="per_hour">Per hour</option>
            <option value="per_day">Per day</option>
            <option value="per_km">Per km (distance)</option>
          </Select>
          <Input label="Rate (USD)" type="number" step="0.01" min="0"
                 error={errors.rate_usd?.message} {...register('rate_usd')} />
        </div>
        {unit === 'per_km' && (
          <p className="rounded-md border border-bordr bg-bgs2 p-2.5 text-xs text-inkm">
            Distance services show “billed by distance — agree with your provider”
            instead of an upfront estimate.
          </p>
        )}
        <Input label="Default duration (minutes, optional)" type="number" min="1"
               error={errors.default_duration_minutes?.message}
               {...register('default_duration_minutes')} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => navigate('/provider/services')}>Back</Button>
          <Button type="submit" loading={isSubmitting}>{isNew ? 'Create' : 'Save'}</Button>
        </div>
      </form>
    </div>
  );
}
