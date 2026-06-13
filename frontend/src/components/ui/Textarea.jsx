import React, { forwardRef } from 'react';

export const Textarea = forwardRef(function Textarea(
  { label, error, hint, id, className = '', rows = 4, ...rest },
  ref
) {
  const inputId = id || rest.name;
  return (
    <div className="w-full">
      {label && <label htmlFor={inputId} className="label">{label}</label>}
      <textarea
        id={inputId}
        ref={ref}
        rows={rows}
        className={`input-base ${error ? 'border-danger/60 focus:ring-danger/30' : ''} ${className}`}
        {...rest}
      />
      {error ? (
        <p className="mt-1 text-xs text-danger">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-inkm">{hint}</p>
      ) : null}
    </div>
  );
});
