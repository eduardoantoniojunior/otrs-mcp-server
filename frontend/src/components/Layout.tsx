import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Key,
  Users,
  ScrollText,
  Settings,
  Terminal,
  LogOut,
  Server,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useHealth } from '../hooks/useTickets';

const navSections = [
  {
    items: [
      { path: '/', label: 'Dashboard', icon: LayoutDashboard },
      { path: '/mcp-tokens', label: 'MCP Tokens', icon: Key },
      { path: '/admin-users', label: 'Admin Users', icon: Users },
    ],
  },
  {
    items: [
      { path: '/client-wizard', label: 'Client MCP Wizard', icon: Terminal },
      { path: '/audit-log', label: 'Audit Log', icon: ScrollText },
      { path: '/login-audit', label: 'Login Audit', icon: ShieldAlert },
      { path: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export default function Layout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { data: healthData } = useHealth();

  const isOnline = healthData?.status === 'ok';

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-navy-950 flex flex-col border-r border-white/[0.04] flex-shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent-blue/20 flex items-center justify-center">
              <Server size={20} className="text-accent-blue" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">OTRS MCP</h1>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {section.items.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={isActive(path) ? 'nav-link-active' : 'nav-link-inactive'}
                >
                  <Icon size={18} />
                  <span>{label}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/[0.06] text-center">
          <p className="text-[11px] text-gray-600 font-mono">v0.2.0</p>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-12 bg-navy-950/50 backdrop-blur-sm border-b border-white/[0.04] flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className={isOnline ? 'status-dot-online' : 'status-dot-offline'} />
            <span className="text-xs text-gray-400">
              MCP available at{' '}
              <code className="text-gray-300 bg-white/[0.04] px-1.5 py-0.5 rounded text-[11px]">
                MCP: /mcp
              </code>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <div className="w-5 h-5 rounded-full bg-accent-blue/20 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-accent-blue">
                  {user?.username?.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="text-xs text-gray-300 font-medium">{user?.username}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-rose-400 transition-colors px-2 py-1 rounded-lg hover:bg-white/[0.04]"
              title="Logout"
            >
              <LogOut size={13} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
