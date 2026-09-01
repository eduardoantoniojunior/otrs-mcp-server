import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';

// Base path para subpath deploy (mesmo valor que Vite injeta)
const API_BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') + '/api';

interface User {
  user_id: number;
  username: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Renovar o token quando faltar 10 minutos para expirar
const REFRESH_MARGIN_MS = 10 * 60 * 1000;

/**
 * Decodifica o payload de um JWT sem validar a assinatura.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

/**
 * Retorna quantos milissegundos faltam para o token expirar.
 * Retorna 0 se expirado ou indecodificavel.
 */
function msUntilExpiry(token: string): number {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return 0;
  return Math.max(0, payload.exp * 1000 - Date.now());
}

/**
 * Verifica se um JWT ainda nao expirou (com margem de 60s).
 */
function isTokenValid(token: string): boolean {
  return msUntilExpiry(token) > 60_000;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRefreshTimer = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
      refreshTimerRef.current = null;
    }
  }, []);

  const logout = useCallback(() => {
    clearRefreshTimer();
    localStorage.removeItem('otrs_token');
    localStorage.removeItem('otrs_user');
    setToken(null);
    setUser(null);
  }, [clearRefreshTimer]);

  /**
   * Agenda o refresh automatico do token.
   * Chama POST /api/admin/refresh quando faltam 10min para expirar.
   */
  const scheduleRefresh = useCallback((currentToken: string) => {
    clearRefreshTimer();

    const remaining = msUntilExpiry(currentToken);
    if (remaining <= 0) return;

    // Agendar refresh para (remaining - margem), minimo 30s
    const delay = Math.max(30_000, remaining - REFRESH_MARGIN_MS);

    refreshTimerRef.current = setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE}/admin/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`,
          },
        });

        if (!response.ok) {
          // Token expirou ou foi invalidado — forcar logout
          logout();
          return;
        }

        const data = await response.json();
        const newToken = data.access_token;

        localStorage.setItem('otrs_token', newToken);
        localStorage.setItem('otrs_user', JSON.stringify({
          user_id: data.user_id,
          username: data.username,
        }));
        setToken(newToken);
        setUser({ user_id: data.user_id, username: data.username });

        // Agendar proximo refresh
        scheduleRefresh(newToken);
      } catch {
        // Erro de rede — tentar de novo em 60s
        refreshTimerRef.current = setTimeout(() => {
          const t = localStorage.getItem('otrs_token');
          if (t && isTokenValid(t)) scheduleRefresh(t);
        }, 60_000);
      }
    }, delay);
  }, [clearRefreshTimer, logout]);

  // Bootstrap: restaurar sessao do localStorage com validacao
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('otrs_token');
      const storedUser = localStorage.getItem('otrs_user');

      if (storedToken && storedUser) {
        if (isTokenValid(storedToken)) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          scheduleRefresh(storedToken);
        } else {
          localStorage.removeItem('otrs_token');
          localStorage.removeItem('otrs_user');
        }
      }
    } catch {
      localStorage.removeItem('otrs_token');
      localStorage.removeItem('otrs_user');
    }
    setIsLoading(false);
  }, [scheduleRefresh]);

  // Cleanup no unmount
  useEffect(() => {
    return () => clearRefreshTimer();
  }, [clearRefreshTimer]);

  const login = async (username: string, password: string) => {
    const response = await fetch(`${API_BASE}/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Credenciais invalidas' }));
      throw new Error(error.detail || 'Erro ao fazer login');
    }

    const data = await response.json();
    const newToken = data.access_token;

    localStorage.setItem('otrs_token', newToken);
    localStorage.setItem('otrs_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
    setToken(newToken);
    setUser({ user_id: data.user_id, username: data.username });
    scheduleRefresh(newToken);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
}
