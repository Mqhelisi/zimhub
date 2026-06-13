import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { notificationsApi } from '../api/notifications.js';
import { useAuth } from './AuthContext.jsx';

const NotificationsContext = createContext(null);

export function NotificationsProvider({ children }) {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }
    setLoading(true);
    try {
      const { notifications, unread_count } = await notificationsApi.list();
      setNotifications(notifications || []);
      setUnreadCount(unread_count || 0);
    } catch (_) {
      // tolerate transient errors
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
    if (user) {
      // Light polling — every 30s while a user is signed in. Acceptable
      // for Stage 1; Stage 2+ may swap to SSE.
      pollRef.current = setInterval(refresh, 30000);
      return () => clearInterval(pollRef.current);
    }
  }, [user, refresh]);

  const markRead = async (id) => {
    await notificationsApi.markRead(id);
    await refresh();
  };
  const markAllRead = async () => {
    await notificationsApi.markAllRead();
    await refresh();
  };

  return (
    <NotificationsContext.Provider value={{ notifications, unreadCount, loading, refresh, markRead, markAllRead }}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationsProvider');
  return ctx;
}
