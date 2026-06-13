import React from 'react';
import { STATUS_LABELS, STATUS_TONE } from '../api.js';

const TONE_CLASS = {
  warning: 'bg-warning/10 text-warning border-warning/30',
  info:    'bg-services/10 text-services border-services/30',
  success: 'bg-success/15 text-success border-success/30',
  danger:  'bg-danger/15 text-danger border-danger/30',
  muted:   'bg-inkm/10 text-inkm border-inkm/20',
};

export function PurchaseStatusBadge({ status, className = '' }) {
  const label = STATUS_LABELS[status] || status;
  const tone = STATUS_TONE[status] || 'muted';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE_CLASS[tone]} ${className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {label}
    </span>
  );
}
