import { Link } from 'react-router-dom';
import { useTickets } from '../hooks/useTickets';
import { Ticket, Plus, AlertCircle, CheckCircle, Clock } from 'lucide-react';

export default function Dashboard() {
  const { data, isLoading, error } = useTickets({ limit: 10 });

  const tickets = data?.TicketID ?? [];
  const total = tickets.length;

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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Ticket className="text-blue-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Tickets Recentes</p>
              <p className="text-2xl font-bold">{total}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <Clock className="text-yellow-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">Sistema</p>
              <p className="text-2xl font-bold text-green-600">Online</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center gap-3">
            <CheckCircle className="text-green-600" size={24} />
            <div>
              <p className="text-sm text-gray-500">API</p>
              <p className="text-2xl font-bold text-green-600">Ativo</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Tickets Recentes</h2>
        </div>
        <div className="p-4">
          {isLoading && <p className="text-gray-500">Carregando...</p>}
          {error && (
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle size={18} />
              <span>Erro ao carregar tickets</span>
            </div>
          )}
          {total === 0 && !isLoading && (
            <p className="text-gray-500">Nenhum ticket encontrado</p>
          )}
          {total > 0 && (
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
