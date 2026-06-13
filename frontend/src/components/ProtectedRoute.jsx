import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { Spinner } from './ui/Card.jsx';

export function ProtectedRoute({ role, children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-[70vh] items-center justify-center">
        <Spinner size={24} />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  // Forced password change short-circuit — only /change-password and /logout are reachable.
  if (user.password_reset_required && !location.pathname.startsWith('/change-password')) {
    return <Navigate to="/change-password" replace />;
  }
  if (role === 'super_admin' && !user.is_super_admin) {
    return (
      <div className="container-page py-24 text-center">
        <h1 className="font-display text-4xl text-ink">403</h1>
        <p className="mt-2 text-inkm">You don't have access to this area.</p>
      </div>
    );
  }
  return children;
}
