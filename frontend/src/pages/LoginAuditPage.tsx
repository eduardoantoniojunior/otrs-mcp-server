import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ShieldAlert, Filter, RefreshCw, CheckCircle, XCircle, Download } from 'lucide-react';
import { api } from '../services/api';

interface LoginAttempt {
  id: number;
  username: string;
  success: boolean;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export default function LoginAuditPage() {
  const [filters, setFilters] = useState({
    username: '',
    success: '' as '' | 'true' | 'false',
    limit: 50,
  });

  const { data: attempts, isLoading, refetch, dataUpdatedAt } = useQuery<LoginAttempt[]>({
    queryKey: ['login-audit', filters],
    queryFn: () => api.getLoginAudit({
      limit: filters.limit,
      username: filters.username || undefined,
      success: filters.success === '' ? undefined : filters.success === 'true',
    }),
    refetchInterval: 30000,
  });

  const successCount = attempts?.filter(a => a.success).length ?? 0;
  const failedCount = attempts?.filter(a => !a.success).length ?? 0;

  const exportData = (format: 'csv' | 'json') => {
    if (!attempts) return;

    let content: string;
    let filename: string;
    let mimeType: string;

    if (format === 'json') {
      content = JSON.stringify(attempts, null, 2);
      filename = `login-audit-${new Date().toISOString().split('T')[0]}.json`;
      mimeType = 'application/json';
    } else {
      const headers = ['ID', 'Username', 'Success', 'IP Address', 'User Agent', 'Timestamp'];
      const rows = attempts.map(a => [
        a.id,
        a.username,
        a.success ? 'Yes' : 'No',
        a.ip_address || '',
        a.user_agent || '',
        a.created_at,
      ]);
      content = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n');
      filename = `login-audit-${new Date().toISOString().split('T')[0]}.csv`;
      mimeType = 'text/csv';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Login Audit</h1>
          <p className="section-subtitle">
            Authentication attempts history
            {attempts && (
              <span className="ml-2 text-gray-500">
                — {successCount} successful, {failedCount} failed
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <div className="relative group">
            <button className="btn-secondary">
              <Download size={14} />
              Export
            </button>
            <div className="absolute right-0 mt-1 w-32 bg-navy-900 border border-white/10 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => exportData('csv')}
                className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-white/5 rounded-t-lg"
              >
                Export CSV
              </button>
              <button
                onClick={() => exportData('json')}
                className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-white/5 rounded-b-lg"
              >
                Export JSON
              </button>
            </div>
          </div>
          <button
            onClick={() => refetch()}
            className="btn-secondary"
            title="Refresh"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card">
          <div className="stat-icon bg-accent-blue/10">
            <ShieldAlert size={22} className="text-accent-blue" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{attempts?.length ?? 0}</p>
            <p className="text-sm text-gray-400 mt-0.5">Total Attempts</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon bg-accent-emerald/10">
            <CheckCircle size={22} className="text-emerald-400" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{successCount}</p>
            <p className="text-sm text-gray-400 mt-0.5">Successful</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon bg-accent-rose/10">
            <XCircle size={22} className="text-rose-400" />
          </div>
          <div>
            <p className="text-3xl font-bold text-white">{failedCount}</p>
            <p className="text-sm text-gray-400 mt-0.5">Failed</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={14} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-300">Filters</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <input
            type="text"
            value={filters.username}
            onChange={(e) => setFilters({ ...filters, username: e.target.value })}
            className="input-dark text-sm"
            placeholder="Filter by username..."
          />
          <select
            value={filters.success}
            onChange={(e) => setFilters({ ...filters, success: e.target.value as '' | 'true' | 'false' })}
            className="input-dark text-sm"
          >
            <option value="">All results</option>
            <option value="true">Successful only</option>
            <option value="false">Failed only</option>
          </select>
          <select
            value={filters.limit}
            onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value) })}
            className="input-dark text-sm"
          >
            <option value={25}>25 records</option>
            <option value={50}>50 records</option>
            <option value={100}>100 records</option>
            <option value={200}>200 records</option>
          </select>
        </div>
        <div className="mt-2 text-[11px] text-gray-600">
          Auto-refresh every 30s · Last update: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('pt-BR') : '—'}
        </div>
      </div>

      {/* Attempts Table */}
      <div className="glass-card overflow-hidden">
        <table className="table-dark">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Username</th>
              <th>Result</th>
              <th>IP Address</th>
              <th>User Agent</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-500">Loading...</td>
              </tr>
            ) : !attempts || attempts.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-8 text-gray-500">
                  <ShieldAlert size={24} className="mx-auto mb-2 text-gray-600" />
                  No login attempts found
                </td>
              </tr>
            ) : (
              attempts.map((attempt) => (
                <tr key={attempt.id}>
                  <td className="whitespace-nowrap text-xs font-mono text-gray-400">
                    {new Date(attempt.created_at).toLocaleString('pt-BR', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </td>
                  <td className="text-sm font-medium text-gray-200">
                    {attempt.username}
                  </td>
                  <td>
                    {attempt.success ? (
                      <span className="badge-green">Success</span>
                    ) : (
                      <span className="badge-rose">Failed</span>
                    )}
                  </td>
                  <td className="text-sm font-mono text-gray-400">
                    {attempt.ip_address || '—'}
                  </td>
                  <td className="text-xs text-gray-500 max-w-[250px] truncate" title={attempt.user_agent || ''}>
                    {attempt.user_agent || '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
