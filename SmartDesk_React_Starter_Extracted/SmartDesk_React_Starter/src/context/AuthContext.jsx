import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { ApiError, apiClientEvents, clearCsrfToken, loginRequest, logoutRequest } from '../api/client';
import { authApi } from '../api/resources';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setAuthError('');
    try {
      const currentUser = await authApi.me();
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
        clearCsrfToken();
        return null;
      }
      setAuthError(error.message || 'Unable to reach the SmartDesk API.');
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    const onSessionExpired = () => {
      if (!mounted) return;
      setUser(null);
      setAuthError('');
      clearCsrfToken();
    };
    window.addEventListener(apiClientEvents.sessionExpired, onSessionExpired);
    authApi.me().then((currentUser) => {
      if (mounted) setUser(currentUser);
    }).catch((error) => {
      if (!mounted) return;
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
        clearCsrfToken();
      } else {
        setAuthError(error.message || 'Unable to reach the SmartDesk API.');
      }
    }).finally(() => { if (mounted) setLoading(false); });
    document.documentElement.dataset.theme = localStorage.getItem('smartdesk.theme') || 'dark';
    return () => {
      mounted = false;
      window.removeEventListener(apiClientEvents.sessionExpired, onSessionExpired);
    };
  }, []);

  const login = useCallback(async (identifier, password) => {
    setLoading(true);
    setAuthError('');
    try {
      const authenticatedUser = await loginRequest(identifier, password);
      setUser(authenticatedUser);
      return authenticatedUser;
    } catch (error) {
      setAuthError(error.message || 'Sign-in failed.');
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setAuthError('');
  }, []);

  const value = useMemo(() => ({
    user,
    isAuthenticated: Boolean(user),
    loading,
    authError,
    refresh,
    login,
    logout,
  }), [user, loading, authError, refresh, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
