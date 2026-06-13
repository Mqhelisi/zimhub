import React from 'react';
import { formatRelative } from '../../../utils/time.js';
import { STATUS_LABELS } from '../api.js';

export function PurchaseEventTimeline({ events = [] }) {
  if (!events.length) return null;
  return (
    <ol className="relative ml-3 border-l border-bordr">
      {events.map((e, i) => (
        <li key={e.id || i} className="ms-4 py-2">
          <div className="absolute -start-1.5 mt-1.5 h-3 w-3 rounded-full border border-bordr bg-bgs2" />
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-sm text-ink">
              {STATUS_LABELS[e.to_status] || e.to_status}
            </span>
            <span className="text-xs text-inkm">
              by {e.actor_role}
              {e.created_at ? ` • ${formatRelative(e.created_at)}` : ''}
            </span>
          </div>
          {e.note && <p className="mt-0.5 text-sm text-inkm">{e.note}</p>}
        </li>
      ))}
    </ol>
  );
}
