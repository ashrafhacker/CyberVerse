'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api, clearTokens, getTokens, setTokens } from './api';
import type { User } from './types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, fullName: string, username: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const data = await api.get<{ data: User }>('/auth/me');
      setUser(data.data);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const tokens = getTokens();
    if (tokens.access) {
      refreshUser().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<{
      data: {
        access_token: string;
        refresh_token: string;
        user: User;
      };
    }>('/auth/login', { email, password }, { auth: false });
    const tokens = data.data;
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(tokens.user);
    return tokens.user;
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string, username: string) => {
      const data = await api.post<{
        data: {
          access_token: string;
          refresh_token: string;
          user: User;
        };
      }>(
        '/auth/register',
        { email, password, full_name: fullName, username },
        { auth: false },
      );
      const tokens = data.data;
      setTokens(tokens.access_token, tokens.refresh_token);
      setUser(tokens.user);
      return tokens.user;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout');
    } catch {
      // ignore network errors on logout
    }
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
