import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

let nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((toast) => {
    const id = nextId++;
    const t = {
      id,
      tone: toast.tone || 'info',
      title: toast.title || '',
      body: toast.body || '',
      duration: toast.duration ?? 6000,
    };
    setToasts((prev) => [...prev, t]);
    if (t.duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((x) => x.id !== id));
      }, t.duration);
    }
    return id;
  }, []);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const api = {
    push,
    dismiss,
    success: (title, body) => push({ tone: 'success', title, body }),
    error: (title, body) => push({ tone: 'error', title, body, duration: 9000 }),
    info: (title, body) => push({ tone: 'info', title, body }),
  };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={[
              'pointer-events-auto card flex items-start gap-3 p-3 shadow-lg',
              t.tone === 'success' && 'border-success/40',
              t.tone === 'error' && 'border-danger/40',
              t.tone === 'info' && 'border-brand/40',
            ].filter(Boolean).join(' ')}
          >
            <div className="mt-0.5">
              {t.tone === 'success' && <CheckCircle2 size={18} className="text-success" />}
              {t.tone === 'error' && <AlertCircle size={18} className="text-danger" />}
              {t.tone === 'info' && <Info size={18} className="text-brand" />}
            </div>
            <div className="min-w-0 flex-1">
              {t.title && <div className="text-sm font-semibold text-ink">{t.title}</div>}
              {t.body && <div className="mt-0.5 break-words text-sm text-inkm whitespace-pre-wrap">{t.body}</div>}
            </div>
            <button onClick={() => dismiss(t.id)} className="text-inkm hover:text-ink" aria-label="Dismiss">
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
