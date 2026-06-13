import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { systemApi } from '../api/system.js';

const DemoModeContext = createContext(null);

export function DemoModeProvider({ children }) {
  const [demoMode, setDemoMode] = useState(true);
  const [defaultCurrency, setDefaultCurrency] = useState('USD');
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const { demo_mode, default_currency } = await systemApi.publicConfig();
      setDemoMode(Boolean(demo_mode));
      setDefaultCurrency(default_currency || 'USD');
    } catch (_) {
      // ignore; banner falls back to off
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <DemoModeContext.Provider value={{ demoMode, defaultCurrency, loaded, refresh }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  const ctx = useContext(DemoModeContext);
  if (!ctx) throw new Error('useDemoMode must be used within DemoModeProvider');
  return ctx;
}
