import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ScrollText, Filter, RefreshCw } from 'lucide-react';
import { api } from '../services/api';

const TOOL_OPTIONS = [
  { value: '', label: 'All actions' },
  { value: 'create_ticket', label: 'create_ticket' },
  { value: 'get_ticket', label: 'get_ticket' },
  { value: 'search_tickets', label: 'search_tickets' },
  { value: 'update_ticket', label: 'update_ticket' },
  { value: 'get_ticket_history', label: 'get_ticket_history' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'success', label: 'Success' },
  { value: 'error', label: 'Error' },
];

export default function AuditLogPage() {
  const [filters, setFilters] = useState({
    tool: '',
    status: '',
    agent: '',
    limit: 50,
  });

  const { data, isLoading, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['admin-activity', filters],
    queryFn: () => api.getAdminActivity({
      limit: filters.limit,
      tool: filters.tool || undefined,
      status: filters.status || undefined,
      agent: filters.agent || undefined,
    }),
    refetchInterval: 10000,
  });

  const events = data?.events ?? [];
  const summary = data?.summary;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <p className="section-subtitle">
            API activity and tool usage history
            {summary && (
              <span className="ml-2 text-gray-500">
                — {summary.total} total ({summary.success_count} success, {summary.error_count} errors)
              </span>
            )}
          </p>
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

      {/* Filters */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={14} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-300">Filters</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <select
            value={filters.tool}
            onChange={(e) => setFilters({ ...filters, tool: e.target.value })}
            className="input-dark text-sm"
          >
            {TOOL_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="input-dark text-sm"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={filters.agent}
            onChange={(e) => setFilters({ ...filters, agent: e.target.value })}
            className="input-dark text-sm"
            placeholder="Filter by agent..."
          />
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
          Auto-refresh every 10s · Last update: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('pt-BR') : '—'}
        </div>
      </div>

      {/* Events Table */}
      <div className="glass-card overflow-hidden">
        <table className="table-dark">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Status</th>
              <th>Agent</th>
              <th>Ticket</th>
              <th>Duration</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">Loading...</td>
              </tr>
            ) : events.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-500">
                  <ScrollText size={24} className="mx-auto mb-2 text-gray-600" />
                  No activity records found
                </td>
              </tr>
            ) : (
              events.map((event) => (
                <tr key={event.id}>
                  <td className="whitespace-nowrap text-xs font-mono text-gray-400">
                    {new Date(event.created_at).toLocaleString('pt-BR', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </td>
                  <td>
                    <span className="badge-blue">{event.tool}</span>
                  </td>
                  <td>
                    <span className={event.status === 'success' ? 'badge-green' : 'badge-rose'}>
                      {event.status}
                    </span>
                  </td>
                  <td className="text-sm text-accent-blue">
                    {event.agent_name || '—'}
                  </td>
                  <td className="text-sm font-mono">
                    {event.ticket_id ? `#${event.ticket_id}` : '—'}
                  </td>
                  <td className="text-xs font-mono text-gray-400">
                    {event.duration_ms?.toFixed(0)}ms
                  </td>
                  <td className="text-xs text-gray-500 max-w-[200px] truncate">
                    {event.error ? (
                      <span className="text-rose-400" title={event.error}>
                        {event.error.substring(0, 60)}
                      </span>
                    ) : event.params ? (
                      <span title={JSON.stringify(event.params)}>
                        {JSON.stringify(event.params).substring(0, 60)}
                      </span>
                    ) : '—'}
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
