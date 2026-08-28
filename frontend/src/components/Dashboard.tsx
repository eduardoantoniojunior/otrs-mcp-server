import { Link } from 'react-router-dom';
import { useHealth, useActivitySummary, useActivity } from '../hooks/useTickets';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import {
  Key,
  Server,
  Users,
  Activity,
  Plus,
  Zap,
  TrendingUp,
  ShieldAlert,
  AlertTriangle,
  Clock,
  XCircle,
} from 'lucide-react';

const TOOL_LABELS: Record<string, string> = {
  create_ticket: 'create_ticket',
  get_ticket: 'get_ticket',
  search_tickets: 'search_tickets',
  update_ticket: 'update_ticket',
  get_ticket_history: 'get_ticket_history',
};

function isExpiringSoon(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  const expires = new Date(expiresAt);
  const now = new Date();
  const diffDays = (expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return diffDays > 0 && diffDays <= 7;
}

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  return new Date(expiresAt) < new Date();
}

function daysUntilExpiry(expiresAt: string | null): number | null {
  if (!expiresAt) return null;
  const expires = new Date(expiresAt);
  const now = new Date();
  return Math.ceil((expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

export default function Dashboard() {
  const { data: healthData, isLoading: healthLoading } = useHealth();
  const { data: summary, isLoading: summaryLoading } = useActivitySummary();
  const { data: activityData } = useActivity({ limit: 10 });

  const { data: apiKeys } = useQuery({
    queryKey: ['api-keys-count'],
    queryFn: () => api.listApiKeys(false),
  });

  const { data: adminUsers } = useQuery({
    queryKey: ['admin-users-count'],
    queryFn: () => api.listUsers(),
  });

  const { data: loginAudit } = useQuery({
    queryKey: ['login-audit-recent'],
    queryFn: () => api.getLoginAudit({ limit: 50 }),
  });

  const isOnline = healthData?.status === 'ok';
  const events = activityData?.events ?? [];
  const tokenCount = apiKeys?.length ?? 0;
  const userCount = adminUsers?.length ?? 0;
  const totalCalls = summary?.total_calls ?? 0;

  // Security stats
  const recentFailedLogins = loginAudit?.filter(a => !a.success).slice(0, 5) ?? [];
  const failedLoginCount = loginAudit?.filter(a => !a.success).length ?? 0;
  const expiringTokens = apiKeys?.filter(k => isExpiringSoon(k.expires_at) && !isExpired(k.expires_at)) ?? [];
  const expiredTokens = apiKeys?.filter(k => isExpired(k.expires_at)) ?? [];
  const neverUsedTokens = apiKeys?.filter(k => k.usage_count === 0 && k.active) ?? [];

  const hasSecurityAlerts = failedLoginCount > 0 || expiringTokens.length > 0 || expiredTokens.length > 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="section-subtitle">System overview and recent activity</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* MCP Tokens */}
        <div className="stat-card">
          <div className="stat-icon bg-amber-500/10">
            <Key size={22} className="text-amber-400" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{tokenCount}</p>
            <p className="text-sm text-gray-400 mt-0.5">MCP Tokens</p>
          </div>
        </div>

        {/* OTRS Server */}
        <div className="stat-card">
          <div className="stat-icon bg-accent-blue/10">
            <Server size={22} className="text-accent-blue" />
          </div>
          <div>
            {healthLoading ? (
              <p className="text-lg font-bold text-gray-400">Checking...</p>
            ) : (
              <>
                <p className="text-3xl font-bold text-white">1</p>
                <p className="text-sm text-gray-400 mt-0.5">OTRS Server</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <div className={isOnline ? 'status-dot-online' : 'status-dot-offline'} />
                  <span className={`text-xs ${isOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {isOnline ? 'Connected' : 'Offline'}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Admin Users */}
        <div className="stat-card">
          <div className="stat-icon bg-accent-cyan/10">
            <Users size={22} className="text-cyan-400" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{userCount}</p>
            <p className="text-sm text-gray-400 mt-0.5">Admin Users</p>
          </div>
        </div>

        {/* Total Calls */}
        <div className="stat-card">
          <div className="stat-icon bg-accent-violet/10">
            <Activity size={22} className="text-violet-400" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{totalCalls}</p>
            <p className="text-sm text-gray-400 mt-0.5">Total API Calls</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3">
        <Link to="/mcp-tokens" className="btn-primary">
          <Plus size={16} />
          Create Token
        </Link>
        <Link to="/settings" className="btn-secondary">
          <Zap size={16} />
          Test OTRS Connection
        </Link>
      </div>

      {/* Security Alerts Card */}
      {hasSecurityAlerts && (
        <div className="glass-card p-5 border-amber-500/20">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert size={18} className="text-amber-400" />
            <h2 className="section-title">Security Alerts</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Failed Logins */}
            {failedLoginCount > 0 && (
              <div className="bg-navy-900/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle size={16} className="text-rose-400" />
                  <span className="text-sm font-medium text-gray-200">Failed Logins</span>
                </div>
                <p className="text-2xl font-bold text-rose-400 mb-2">{failedLoginCount}</p>
                <div className="space-y-1">
                  {recentFailedLogins.slice(0, 3).map((attempt, i) => (
                    <div key={i} className="text-xs text-gray-400 flex justify-between">
                      <span>{attempt.username}</span>
                      <span>{new Date(attempt.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  ))}
                </div>
                <Link to="/login-audit" className="text-xs text-accent-blue hover:underline mt-2 block">
                  View all →
                </Link>
              </div>
            )}

            {/* Expiring Tokens */}
            {expiringTokens.length > 0 && (
              <div className="bg-navy-900/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={16} className="text-amber-400" />
                  <span className="text-sm font-medium text-gray-200">Expiring Soon</span>
                </div>
                <p className="text-2xl font-bold text-amber-400 mb-2">{expiringTokens.length}</p>
                <div className="space-y-1">
                  {expiringTokens.slice(0, 3).map((token) => (
                    <div key={token.id} className="text-xs text-gray-400 flex justify-between">
                      <span className="truncate max-w-[100px]">{token.name}</span>
                      <span>{daysUntilExpiry(token.expires_at)}d left</span>
                    </div>
                  ))}
                </div>
                <Link to="/mcp-tokens?status=expiring" className="text-xs text-accent-blue hover:underline mt-2 block">
                  Manage tokens →
                </Link>
              </div>
            )}

            {/* Expired Tokens */}
            {expiredTokens.length > 0 && (
              <div className="bg-navy-900/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Clock size={16} className="text-gray-400" />
                  <span className="text-sm font-medium text-gray-200">Expired Tokens</span>
                </div>
                <p className="text-2xl font-bold text-gray-400 mb-2">{expiredTokens.length}</p>
                <p className="text-xs text-gray-500">
                  These tokens are no longer valid and can be deleted.
                </p>
                <Link to="/mcp-tokens?status=expired" className="text-xs text-accent-blue hover:underline mt-2 block">
                  Clean up →
                </Link>
              </div>
            )}

            {/* Never Used Tokens */}
            {neverUsedTokens.length > 0 && !expiredTokens.length && (
              <div className="bg-navy-900/50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Key size={16} className="text-gray-400" />
                  <span className="text-sm font-medium text-gray-200">Never Used</span>
                </div>
                <p className="text-2xl font-bold text-gray-400 mb-2">{neverUsedTokens.length}</p>
                <p className="text-xs text-gray-500">
                  Active tokens that have never been used.
                </p>
                <Link to="/mcp-tokens" className="text-xs text-accent-blue hover:underline mt-2 block">
                  Review →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Active Tasks Panel */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={18} className="text-gray-400" />
            <h2 className="section-title">Active Tasks</h2>
          </div>
          <span className="text-xs text-gray-500">In-memory store for long-running tools</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <div className="flex items-center gap-1 mb-1">
              <span className="text-xs text-gray-400">Live tasks</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {summaryLoading ? '...' : summary?.last_24h?.calls ?? 0}
              <span className="text-sm font-normal text-gray-500 ml-1">/ 100</span>
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {summaryLoading ? '...' : `${Math.min(Math.round(((summary?.last_24h?.calls ?? 0) / 100) * 100), 100)}% capacity`}
            </p>
          </div>
          <div>
            <div className="flex items-center gap-1 mb-1">
              <span className="text-xs text-gray-400">Success rate</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {summaryLoading ? '...' : totalCalls > 0
                ? `${Math.round(((summary?.by_status?.success ?? 0) / totalCalls) * 100)}%`
                : '—'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">Overall success</p>
          </div>
          <div>
            <div className="flex items-center gap-1 mb-1">
              <span className="text-xs text-gray-400">Default TTL</span>
            </div>
            <p className="text-2xl font-bold text-white">60 min</p>
            <p className="text-xs text-gray-500 mt-0.5">When client omits ttl</p>
          </div>
          <div>
            <div className="flex items-center gap-1 mb-1">
              <span className="text-xs text-gray-400">TL caching</span>
            </div>
            <p className="text-2xl font-bold text-white">24 h</p>
            <p className="text-xs text-gray-500 mt-0.5">Max client-supplied</p>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-card">
        <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
          <h2 className="section-title">Recent Activity</h2>
          <Link to="/audit-log" className="text-xs text-accent-blue hover:text-blue-400 transition-colors">
            Latest activity →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="table-dark">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Agent</th>
                <th>Target</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-gray-500">
                    No recent activity
                  </td>
                </tr>
              ) : (
                events.slice(0, 8).map((event, i) => (
                  <tr key={`${event.timestamp}-${i}`} className="animate-fade-in">
                    <td className="whitespace-nowrap text-xs text-gray-400 font-mono">
                      {new Date(event.timestamp_iso).toLocaleString('pt-BR', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td>
                      <span className={event.status === 'success' ? 'badge-green' : 'badge-rose'}>
                        {TOOL_LABELS[event.tool] || event.tool}
                      </span>
                    </td>
                    <td className="text-sm text-accent-blue">
                      {(event as unknown as { agent_name?: string }).agent_name || '—'}
                    </td>
                    <td className="text-sm">
                      {event.ticket_id ? `#${event.ticket_id}` : '—'}
                    </td>
                    <td className="text-xs text-gray-400 font-mono">
                      {event.duration_ms?.toFixed(0)}ms
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
