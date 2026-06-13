import React from 'react';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { formatRelative } from '../../../utils/time.js';

export function DisputeBanner({ dispute }) {
  if (!dispute) return null;
  const resolved = dispute.status === 'resolved';
  return (
    <div
      className={`flex gap-3 rounded-lg border p-4 ${
        resolved
          ? 'border-inkm/30 bg-inkm/5'
          : 'border-danger/40 bg-danger/10'
      }`}
    >
      <div className="mt-0.5 shrink-0">
        {resolved ? (
          <ShieldCheck size={18} className="text-inkm" />
        ) : (
          <AlertTriangle size={18} className="text-danger" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="font-medium text-ink">
            {resolved ? `Dispute resolved — ${dispute.resolution}` : 'Dispute open'}
          </span>
          {dispute.created_at && (
            <span className="text-xs text-inkm">
              raised {formatRelative(dispute.created_at)} by {dispute.raised_by_role}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-inkm whitespace-pre-wrap">{dispute.reason}</p>
        {resolved && dispute.resolution_note && (
          <p className="mt-2 text-sm text-ink">
            <span className="font-medium">Admin note: </span>{dispute.resolution_note}
          </p>
        )}
      </div>
    </div>
  );
}
