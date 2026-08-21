import { Link } from 'react-router-dom';
import { useTickets, useHealth, useActivitySummary, useActivity } from '../hooks/useTickets';
import {
  Plus,
  CheckCircle,
  Clock,
  Search,
  Ticket as TicketIcon,
  Edit3,
  History,
  Activity,
  TrendingUp,
  XCircle,
} from 'lucide-react';

const TOOL_LABELS: Record<string, string> = {
  create_ticket: 'Criar Ticket',
  get_ticket: 'Consultar Ticket',
  search_tickets: 'Buscar Tickets',
  update_ticket: 'Atualizar Ticket',
  get_ticket_history: 'Historico',
};

const TOOL_ICONS: Record<string, typeof Search> = {
  create_ticket: Plus,
  get_ticket: TicketIcon,
  search_tickets: Search,
  update_ticket: Edit3,
  get_ticket_history: History,
};

export default function Dashboard() {
  const { data: healthData, isLoading: healthLoading } = useHealth();
  const { data: summary, isLoading: summaryLoading } = useActivitySummary();
  const { data: activityData } = useActivity({ limit: 10 });
  const { data: ticketsData, isLoading: ticketsLoading } = useTickets({ limit: 5 });

  const apiOnline = healthData?.status === 'ok';
  const tickets = ticketsData?.TicketID ?? [];
  const events = activityData?.events ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link
          to="/tickets/new"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={18} />
          Novo Ticket
        </Link>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Activity className="text-purple-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Total de Chamadas</p>
              {summaryLoading ? (
                <p className="text-2xl font-bold text-gray-400">...</p>
              ) : (
                <p className="text-2xl font-bold">{summary?.total_calls ?? 0}</p>
              )}
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="text-blue-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Ultimas 24h</p>
              {summaryLoading ? (
                <p className="text-2xl font-bold text-gray-400">...</p>
              ) : (
                <p className="text-2xl font-bold">{summary?.last_24h?.calls ?? 0}</p>
              )}
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Sucesso</p>
              {summaryLoading ? (
                <p className="text-2xl font-bold text-gray-400">...</p>
              ) : (
                <p className="text-2xl font-bold text-green-600">
                  {summary?.by_status?.success ?? 0}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <XCircle className="text-red-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Erros</p>
              {summaryLoading ? (
                <p className="text-2xl font-bold text-gray-400">...</p>
              ) : (
                <p className="text-2xl font-bold text-red-600">
                  {summary?.by_status?.error ?? 0}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Clock className="text-yellow-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Sistema</p>
              {healthLoading ? (
                <p className="text-lg font-bold text-gray-400">Verificando...</p>
              ) : apiOnline ? (
                <p className="text-lg font-bold text-green-600">Online</p>
              ) : (
                <p className="text-lg font-bold text-red-600">Offline</p>
              )}
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">API</p>
              {healthLoading ? (
                <p className="text-lg font-bold text-gray-400">Verificando...</p>
              ) : apiOnline ? (
                <p className="text-lg font-bold text-green-600">Ativo</p>
              ) : (
                <p className="text-lg font-bold text-red-600">Inativo</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity by Tool */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Atividade por Ferramenta</h2>
          </div>
          <div className="p-4">
            {summaryLoading && <p className="text-gray-500">Carregando...</p>}
            {!summaryLoading && Object.keys(summary?.by_tool ?? {}).length === 0 && (
              <p className="text-gray-500">Nenhuma atividade registrada</p>
            )}
            {!summaryLoading && Object.entries(summary?.by_tool ?? {}).length > 0 && (
              <div className="space-y-3">
                {Object.entries(summary!.by_tool)
                  .sort(([, a], [, b]) => b - a)
                  .map(([tool, count]) => {
                    const Icon = TOOL_ICONS[tool] || Activity;
                    const maxCount = Math.max(...Object.values(summary!.by_tool));
                    const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
                    return (
                      <div key={tool}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <Icon size={16} className="text-gray-400" />
                            <span className="text-sm font-medium">
                              {TOOL_LABELS[tool] || tool}
                            </span>
                          </div>
                          <span className="text-sm font-bold">{count}</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Atividade Recente</h2>
          </div>
          <div className="p-4">
            {events.length === 0 && (
              <p className="text-gray-500">Nenhuma atividade recente</p>
            )}
            {events.length > 0 && (
              <div className="space-y-2">
                {events.slice(0, 8).map((event, i) => {
                  const Icon = TOOL_ICONS[event.tool] || Activity;
                  return (
                    <div
                      key={`${event.timestamp}-${i}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50"
                    >
                      <div
                        className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          event.status === 'success' ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      <Icon size={16} className="text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {TOOL_LABELS[event.tool] || event.tool}
                          {event.ticket_id && (
                            <span className="text-gray-400 ml-1">#{event.ticket_id}</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-400">
                          {event.duration_ms.toFixed(0)}ms
                          {event.error && (
                            <span className="text-red-500 ml-2">
                              {event.error.substring(0, 40)}
                            </span>
                          )}
                        </p>
                      </div>
                      <span className="text-xs text-gray-400 whitespace-nowrap">
                        {new Date(event.timestamp_iso).toLocaleTimeString('pt-BR')}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Tickets */}
      <div className="bg-white rounded-lg shadow mt-6">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Tickets Recentes</h2>
        </div>
        <div className="p-4">
          {ticketsLoading && <p className="text-gray-500">Carregando...</p>}
          {tickets.length === 0 && !ticketsLoading && (
            <p className="text-gray-500">Nenhum ticket encontrado</p>
          )}
          {tickets.length > 0 && (
            <div className="space-y-2">
              {tickets.slice(0, 5).map((ticketId) => (
                <Link
                  key={ticketId}
                  to={`/tickets/${ticketId}`}
                  className="block p-3 rounded-lg hover:bg-gray-50 border"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-gray-500">#{ticketId}</span>
                    <span className="text-xs px-2 py-1 rounded bg-gray-100">Ver detalhes</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
