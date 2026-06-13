import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { UserPlus } from 'lucide-react';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { SuburbSelect } from '../../components/ui/SuburbSelect.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { errMessage, errFieldErrors } from '../../api/client.js';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit, watch, setError, formState: { errors, isSubmitting } } =
    useForm({ defaultValues: { city: 'Bulawayo' } });
  const [submitError, setSubmitError] = useState('');
  const password = watch('password');

  const onSubmit = async (data) => {
    setSubmitError('');
    if (data.password !== data.confirm) {
      setError('confirm', { message: 'Passwords do not match' });
      return;
    }
    try {
      await signup({
        email: data.email,
        phone: data.phone,
        password: data.password,
        name: data.name,
        suburb: data.suburb || null,
        city: data.city || 'Bulawayo',
      });
      navigate('/', { replace: true });
    } catch (err) {
      const fields = errFieldErrors(err);
      if (fields) {
        Object.entries(fields).forEach(([k, v]) => setError(k, { message: v }));
      }
      setSubmitError(errMessage(err, 'Could not create your account.'));
    }
  };

  return (
    <div className="container-narrow">
      <div className="text-center">
        <h1 className="font-display text-4xl text-ink">Create your account</h1>
        <p className="mt-2 text-sm text-inkm">Free to sign up. Sellers apply separately at /sell.</p>
      </div>
      <Card className="mt-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Full name"
            error={errors.name?.message}
            {...register('name', { required: 'Required' })}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register('email', { required: 'Required' })}
            />
            <Input
              label="Phone"
              placeholder="+263 77 …"
              error={errors.phone?.message}
              hint="+263XXXXXXXXX or 07XXXXXXXX"
              {...register('phone', { required: 'Required' })}
            />
          </div>
          <SuburbSelect
            error={errors.suburb?.message}
            {...register('suburb')}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Password"
              type="password"
              autoComplete="new-password"
              hint="At least 8 chars with one number"
              error={errors.password?.message}
              {...register('password', {
                required: 'Required',
                minLength: { value: 8, message: 'Min 8 characters' },
                validate: (v) => /\d/.test(v) || 'Must include a digit',
              })}
            />
            <Input
              label="Confirm password"
              type="password"
              autoComplete="new-password"
              error={errors.confirm?.message}
              {...register('confirm', {
                required: 'Required',
                validate: (v) => v === password || 'Passwords do not match',
              })}
            />
          </div>
          {submitError && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {submitError}
            </div>
          )}
          <Button type="submit" loading={isSubmitting} className="w-full">
            <UserPlus size={16} /> Create account
          </Button>
        </form>
        <div className="mt-5 border-t border-bordr pt-4 text-sm text-inkm">
          Already have an account? <Link to="/login" className="text-brand">Sign in →</Link>
        </div>
      </Card>
    </div>
  );
}
