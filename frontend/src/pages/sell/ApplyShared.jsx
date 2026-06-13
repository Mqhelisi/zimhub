import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useForm, FormProvider } from 'react-hook-form';
import { CheckCircle2 } from 'lucide-react';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Textarea } from '../../components/ui/Textarea.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { SuburbSelect } from '../../components/ui/SuburbSelect.jsx';
import { signupRequestsApi } from '../../api/signupRequests.js';
import { errMessage, errFieldErrors } from '../../api/client.js';

const ACCENT = {
  salesman: '--shop-accent',
  promoter: '--events-accent',
  provider: '--services-accent',
  creator: '--creators-accent',
};

export function ApplyShared({ category, title, lede, businessNameLabel, children, buildPayload }) {
  const methods = useForm();
  const { register, handleSubmit, watch, setError, formState: { errors, isSubmitting } } = methods;
  const [submitError, setSubmitError] = useState('');
  const [done, setDone] = useState(false);

  const pitch = watch('pitch') || '';

  const onSubmit = async (data) => {
    setSubmitError('');
    try {
      const category_payload = buildPayload(data);
      await signupRequestsApi.submit({
        category,
        full_name: data.full_name,
        business_name: data.business_name || null,
        email: data.email,
        phone: data.phone,
        suburb: data.suburb,
        pitch: data.pitch,
        category_payload,
      });
      setDone(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      const fields = errFieldErrors(err);
      if (fields) {
        Object.entries(fields).forEach(([k, v]) => {
          // Field errors like 'category_payload.shop_name' need stripping for RHF field paths.
          const rhfPath = k.replace(/^category_payload\./, '');
          setError(rhfPath, { message: v });
        });
      }
      setSubmitError(errMessage(err, 'Could not submit your application.'));
    }
  };

  if (done) {
    return (
      <div className="container-narrow text-center">
        <div className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-full bg-success/15 text-success">
          <CheckCircle2 size={28} />
        </div>
        <h1 className="mt-5 font-display text-4xl text-ink">Thanks — application received</h1>
        <p className="mt-3 text-inkm">
          We'll review your application personally and email you within 48 hours.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link to="/" className="btn-secondary">Back to home</Link>
          <Link to="/sell" className="btn-ghost">Apply for another category →</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container-narrow">
      <div style={{ '--section': `var(${ACCENT[category]})` }}>
        <span
          className="pill"
          style={{
            borderColor: 'rgb(var(--section) / 0.4)',
            background: 'rgb(var(--section) / 0.12)',
            color: 'rgb(var(--section))',
          }}
        >
          {category.charAt(0).toUpperCase() + category.slice(1)} application
        </span>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl text-ink leading-[1.1]">{title}</h1>
        <p className="mt-3 text-inkm">{lede}</p>
      </div>

      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-7 space-y-5">
          <Card>
            <h3 className="font-display text-xl text-ink">About you</h3>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Input
                label="Full name"
                error={errors.full_name?.message}
                {...register('full_name', { required: 'Required' })}
              />
              <Input
                label={businessNameLabel || 'Business name (optional)'}
                error={errors.business_name?.message}
                {...register('business_name')}
              />
              <Input
                label="Email"
                type="email"
                error={errors.email?.message}
                {...register('email', { required: 'Required' })}
              />
              <Input
                label="Phone"
                placeholder="+263 77 …"
                hint="+263XXXXXXXXX or 07XXXXXXXX"
                error={errors.phone?.message}
                {...register('phone', { required: 'Required' })}
              />
              <SuburbSelect
                error={errors.suburb?.message}
                {...register('suburb', { required: 'Required' })}
              />
            </div>
          </Card>

          <Card>
            <h3 className="font-display text-xl text-ink">Category details</h3>
            <div className="mt-4 grid gap-4">{children}</div>
          </Card>

          <Card>
            <h3 className="font-display text-xl text-ink">Your pitch</h3>
            <Textarea
              rows={5}
              className="mt-4"
              placeholder="In a few sentences, tell us what you do and why ZimHub is a good home for it."
              error={errors.pitch?.message}
              {...register('pitch', {
                required: 'Required',
                maxLength: { value: 500, message: 'Max 500 characters' },
              })}
            />
            <div className="mt-1 text-right text-xs text-inkm">{pitch.length} / 500</div>
          </Card>

          {submitError && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {submitError}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-end gap-3">
            <Link to="/sell" className="btn-ghost">Cancel</Link>
            <Button type="submit" loading={isSubmitting}>Submit application</Button>
          </div>
        </form>
      </FormProvider>
    </div>
  );
}
