import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function Drawer({ open, onClose, title, children, footer, width = 'lg' }) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [open, onClose]);
  if (!open) return null;
  const widths = { md: 'max-w-md', lg: 'max-w-xl', xl: 'max-w-2xl' };
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-bgp/70 backdrop-blur-sm">
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 -z-10 h-full w-full cursor-default"
        tabIndex={-1}
        aria-hidden
      />
      <div className={`relative h-full w-full ${widths[width]} flex flex-col bg-bgs border-l border-bordr`}>
        <div className="flex shrink-0 items-center justify-between border-b border-bordr px-5 py-3.5">
          <h3 className="font-display text-xl text-ink">{title}</h3>
          <button onClick={onClose} className="text-inkm hover:text-ink" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 border-t border-bordr px-5 py-3.5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
