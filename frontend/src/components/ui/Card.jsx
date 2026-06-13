import React from 'react';
import { Loader2 } from 'lucide-react';

export function Card({ className = '', children, ...rest }) {
  return (
    <div className={`card p-5 ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function Spinner({ size = 18, className = '' }) {
  return <Loader2 size={size} className={`animate-spin text-brand ${className}`} />;
}
