import React from 'react';
import { Check } from 'lucide-react';

/**
 * Visual progress along the happy path:
 *   1. Initiated  2. Paid  3. Received
 * If the purchase is terminal in a non-happy way (cancelled/expired/disputed/refunded)
 * a single status pill is rendered instead.
 */
export function PurchaseProgress({ purchase, className = '' }) {
  const s = purchase.status;
  if (['cancelled', 'expired', 'refunded'].includes(s)) return null;

  const stepIndex = {
    awaiting_payment: 0,
    disputed: 1,                       // mid-flow — at least past initiation
    awaiting_buyer_confirmation: 1,
    completed: 2,
  }[s] ?? 0;

  const steps = [
    { key: 'initiated', label: 'Initiated' },
    { key: 'paid',      label: 'Paid' },
    { key: 'received',  label: 'Received' },
  ];

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {steps.map((step, i) => {
        const done = i <= stepIndex;
        const isFinal = i === steps.length - 1;
        return (
          <React.Fragment key={step.key}>
            <div className="flex items-center gap-2 min-w-0">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold transition
                  ${done ? 'bg-brand text-bg' : 'bg-bgs2 text-inkm ring-1 ring-bordr'}`}
              >
                {done ? <Check size={12} /> : i + 1}
              </div>
              <span className={`text-xs ${done ? 'text-ink' : 'text-inkm'}`}>{step.label}</span>
            </div>
            {!isFinal && (
              <div className={`h-px flex-1 min-w-[12px] ${i < stepIndex ? 'bg-brand' : 'bg-border'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
