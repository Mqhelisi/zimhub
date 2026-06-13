import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api/auth.js';
import { setUnauthenticatedHandler } from '../api/client.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [capabilities, setCapabilities] = useState(null);
  const [adminEntries, setAdminEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const { user, capabilities, admin_entries } = await authApi.me();
      setUser(user);
      setCapabilities(capabilities);
      setAdminEntries(admin_entries || []);
    } catch (err) {
      setUser(null);
      setCapabilities(null);
      setAdminEntries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Bounce on global 401s.
    setUnauthenticatedHandler(() => {
      setUser(null);
      setCapabilities(null);
      setAdminEntries([]);
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.assign('/login');
      }
    });
    refresh();
  }, [refresh]);

  const login = async (email, password) => {
    const { user } = await authApi.login(email, password);
    await refresh();
    return user;
  };

  const signup = async (body) => {
    const { user } = await authApi.signup(body);
    await refresh();
    return user;
  };

  const logout = async () => {
    try { await authApi.logout(); } catch (_) {}
    setUser(null);
    setCapabilities(null);
    setAdminEntries([]);
  };

  const value = { user, capabilities, adminEntries, loading, login, signup, logout, refresh };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
