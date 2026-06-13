import React, { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { authApi } from '../../api/auth.js';
import { errMessage } from '../../api/client.js';

export default function PasswordResetConfirm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { register, handleSubmit, watch, setError, formState: { errors, isSubmitting } } = useForm();
  const [err, setErr] = useState('');
  const [done, setDone] = useState(false);

  const password = watch('new_password');

  const onSubmit = async (data) => {
    setErr('');
    if (data.new_password !== data.confirm) {
      setError('confirm', { message: 'Passwords do not match' });
      return;
    }
    try {
      await authApi.passwordResetConfirm(token, data.new_password);
      setDone(true);
      setTimeout(() => navigate('/login', { replace: true }), 1500);
    } catch (e) {
      setErr(errMessage(e, 'Could not reset password.'));
    }
  };

  return (
    <div className="container-narrow">
      <h1 className="font-display text-4xl text-ink text-center">Set a new password</h1>
      <Card className="mt-6">
        {done ? (
          <div className="text-center">
            <h3 className="font-display text-xl text-ink">Password updated</h3>
            <p className="mt-2 text-sm text-inkm">Redirecting to sign in…</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
              Update password
            </Button>
            <div className="text-center text-sm">
              <Link to="/login" className="text-inkm hover:text-brand">Back to sign in</Link>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
