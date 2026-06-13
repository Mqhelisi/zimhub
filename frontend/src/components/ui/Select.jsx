import React, { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

export const Select = forwardRef(function Select(
  { label, error, hint, options = [], id, className = '', children, ...rest },
  ref
) {
  const inputId = id || rest.name;
  return (
    <div className="w-full">
      {label && <label htmlFor={inputId} className="label">{label}</label>}
      <div className="relative">
        <select
          id={inputId}
          ref={ref}
          className={`input-base appearance-none pr-9 ${error ? 'border-danger/60' : ''} ${className}`}
          {...rest}
        >
          {children ||
            options.map((opt) =>
              typeof opt === 'string' ? (
                <option key={opt} value={opt}>{opt}</option>
              ) : (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              )
            )}
        </select>
        <ChevronDown
          size={16}
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-inkm"
        />
      </div>
      {error ? (
        <p className="mt-1 text-xs text-danger">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-inkm">{hint}</p>
      ) : null}
    </div>
  );
});
