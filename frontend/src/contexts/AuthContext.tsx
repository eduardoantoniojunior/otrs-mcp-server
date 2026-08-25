import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem('otrs_token');
    const storedUser = localStorage.getItem('otrs_user');
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Credenciais invalidas' }));
      throw new Error(error.detail || 'Erro ao fazer login');
    }

    const data = await response.json();
    localStorage.setItem('otrs_token', data.access_token);
    localStorage.setItem('otrs_user', JSON.stringify({ user_id: data.user_id, username: data.username }));
    setToken(data.access_token);
    setUser({ user_id: data.user_id, username: data.username });
  };

  const logout = () => {
    localStorage.removeItem('otrs_token');
    localStorage.removeItem('otrs_user');
    setToken(null);
    setUser(null);
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
