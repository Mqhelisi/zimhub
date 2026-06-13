import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import { Card } from '../../components/ui/Card.jsx';
import { Input } from '../../components/ui/Input.jsx';
import { Button } from '../../components/ui/Button.jsx';
import { authApi } from '../../api/auth.js';

export default function PasswordResetRequest() {
  const [email, setEmail] = useState('');
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await authApi.passwordResetRequest(email); } catch (_) {}
    setLoading(false);
    setDone(true);
  };

  return (
    <div className="container-narrow">
      <h1 className="font-display text-4xl text-ink text-center">Reset your password</h1>
      <Card className="mt-6">
        {done ? (
          <div className="text-center">
            <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand/10 text-brand">
              <Mail size={22} />
            </div>
            <h3 className="mt-4 font-display text-xl text-ink">Check your inbox</h3>
            <p className="mt-2 text-sm text-inkm">
              If an account exists for <span className="text-ink">{email}</span>, a reset link is on its way.
              It expires in 1 hour.
            </p>
            <Link to="/login" className="mt-5 inline-block text-sm text-brand">Back to sign in</Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
            <Button type="submit" loading={loading} className="w-full">
              Send reset link
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
