import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function Modal({ open, onClose, title, children, footer, size = 'md' }) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [open, onClose]);

  if (!open) return null;
  const sizes = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-2xl' };
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-bgp/80 backdrop-blur-sm p-4 sm:p-8">
      <div
        className={`relative w-full ${sizes[size]} card mt-8 sm:mt-16 p-0 shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-bordr px-5 py-3.5">
          <h3 className="font-display text-xl text-ink">{title}</h3>
          <button onClick={onClose} className="text-inkm hover:text-ink" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-2 border-t border-bordr px-5 py-3.5">
            {footer}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 -z-10 h-full w-full cursor-default"
        tabIndex={-1}
        aria-hidden
      />
    </div>
  );
}
