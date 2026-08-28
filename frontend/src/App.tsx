import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import Dashboard from './components/Dashboard';
import ApiKeysPage from './pages/ApiKeysPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AuditLogPage from './pages/AuditLogPage';
import LoginAuditPage from './pages/LoginAuditPage';
import SettingsPage from './pages/SettingsPage';
import ClientWizardPage from './pages/ClientWizardPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-navy-900">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-accent-blue" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-navy-900">
        <div className="flex items-center gap-3">
          <svg className="animate-spin h-5 w-5 text-accent-blue" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-gray-400">Loading...</span>
        </div>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="mcp-tokens" element={<ApiKeysPage />} />
            <Route path="admin-users" element={<AdminUsersPage />} />
            <Route path="client-wizard" element={<ClientWizardPage />} />
            <Route path="audit-log" element={<AuditLogPage />} />
            <Route path="login-audit" element={<LoginAuditPage />} />
            <Route path="settings" element={<SettingsPage />} />
            {/* Legacy redirects */}
            <Route path="api-keys" element={<Navigate to="/mcp-tokens" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
