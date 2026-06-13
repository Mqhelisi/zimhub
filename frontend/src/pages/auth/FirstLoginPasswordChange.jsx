import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { Lock } from 'lucide-react';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { authApi } from '../../api/auth.js';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { errMessage } from '../../api/client.js';

export default function FirstLoginPasswordChange() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit, watch, setError, formState: { errors, isSubmitting } } = useForm();
  const [err, setErr] = useState('');
  const password = watch('new_password');

  const onSubmit = async (data) => {
    setErr('');
    if (data.new_password !== data.confirm) {
      setError('confirm', { message: 'Passwords do not match' });
      return;
    }
    try {
      await authApi.passwordChange(data.current_password, data.new_password);
      await refresh();
      navigate(user?.is_super_admin ? '/super' : '/', { replace: true });
    } catch (e) {
      setErr(errMessage(e, 'Could not change password.'));
    }
  };

  return (
    <div className="container-narrow">
      <div className="text-center">
        <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand/10 text-brand">
          <Lock size={22} />
        </div>
        <h1 className="mt-4 font-display text-4xl text-ink">Set your password</h1>
        <p className="mt-2 text-sm text-inkm">
          You're signed in with a temporary password. Pick a new one to continue.
        </p>
      </div>
      <Card className="mt-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Current (temporary) password"
            type="password"
            autoComplete="current-password"
            error={errors.current_password?.message}
            {...register('current_password', { required: 'Required' })}
          />
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            hint="At least 8 chars with one number"
            error={errors.new_password?.message}
            {...register('new_password', {
              required: 'Required',
              minLength: { value: 8, message: 'Min 8 characters' },
              validate: (v) => /\d/.test(v) || 'Must include a digit',
            })}
          />
          <Input
            label="Confirm new password"
            type="password"
            error={errors.confirm?.message}
            {...register('confirm', {
              required: 'Required',
              validate: (v) => v === password || 'Passwords do not match',
            })}
          />
          {err && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {err}
            </div>
          )}
          <Button type="submit" loading={isSubmitting} className="w-full">
            Update password & continue
          </Button>
        </form>
      </Card>
    </div>
  );
}
