import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  getGateToken, getGateMeta, setGateSession, clearGateSession,
  gateMe, gateLogin as apiGateLogin,
} from '../api/index.js';

const GateAuthContext = createContext(null);

export function GateAuthProvider({ children }) {
  const [meta, setMeta] = useState(() => getGateMeta());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // On mount, if we have a token, verify by calling /api/gate/me. If it
  // fails, clear the session.
  useEffect(() => {
    if (!getGateToken()) return;
    setLoading(true);
    gateMe()
      .then((m) => { setMeta(m); setGateSession(getGateToken(), m); })
      .catch(() => { clearGateSession(); setMeta(null); })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async ({ phone, pin, event_id }) => {
    setLoading(true); setError(null);
    try {
      const res = await apiGateLogin({ phone, pin, event_id });
      const newMeta = { gateman: res.gateman, event: res.event };
      setGateSession(res.token, newMeta);
      setMeta(newMeta);
      return res;
    } catch (e) {
      setError(e.message || 'Login failed');
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    clearGateSession();
    setMeta(null);
  }, []);

  return (
    <GateAuthContext.Provider value={{ meta, loading, error, login, logout, isAuthed: !!meta }}>
      {children}
    </GateAuthContext.Provider>
  );
}

export function useGateAuth() {
  const v = useContext(GateAuthContext);
  if (!v) throw new Error('useGateAuth must be used inside GateAuthProvider');
  return v;
}
