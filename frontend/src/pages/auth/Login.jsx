import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { LogIn } from 'lucide-react';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { errMessage } from '../../api/client.js';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const [submitError, setSubmitError] = useState('');

  const onSubmit = async (data) => {
    setSubmitError('');
    try {
      const user = await login(data.email, data.password);
      if (user.password_reset_required) {
        navigate('/change-password', { replace: true });
      } else if (user.is_super_admin) {
        navigate('/super', { replace: true });
      } else {
        const dest = location.state?.from || '/';
        navigate(dest, { replace: true });
      }
    } catch (err) {
      setSubmitError(errMessage(err, 'Could not sign you in.'));
    }
  };

  return (
    <div className="container-narrow">
      <div className="text-center">
        <h1 className="font-display text-4xl text-ink">Welcome back</h1>
        <p className="mt-2 text-sm text-inkm">Sign in to your ZimHub account.</p>
      </div>
      <Card className="mt-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            error={errors.email?.message}
            {...register('email', { required: 'Email is required' })}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register('password', { required: 'Password is required' })}
          />
          {submitError && (
            <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
              {submitError}
            </div>
          )}
          <Button type="submit" loading={isSubmitting} className="w-full">
            <LogIn size={16} /> Sign in
          </Button>
        </form>
        <div className="mt-5 flex items-center justify-between border-t border-bordr pt-4 text-sm">
          <Link to="/password-reset" className="text-inkm hover:text-brand">Forgot password?</Link>
          <Link to="/signup" className="text-brand">Create an account →</Link>
        </div>
      </Card>
    </div>
  );
}
