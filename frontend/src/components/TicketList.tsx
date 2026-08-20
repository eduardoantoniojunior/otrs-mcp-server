import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTickets } from '../hooks/useTickets';
import { Search, ExternalLink } from 'lucide-react';

export default function TicketList() {
  const [search, setSearch] = useState('');
  const [queue, setQueue] = useState('');
  const [state, setState] = useState('');
  const [priority, setPriority] = useState('');

  const { data, isLoading, error } = useTickets({
    title: search || undefined,
    queue: queue || undefined,
    state: state || undefined,
    priority: priority || undefined,
    limit: 50,
  });

  const ticketIds = data?.TicketID ?? [];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Tickets</h1>

      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="Buscar por titulo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <select
            value={queue}
            onChange={(e) => setQueue(e.target.value)}
            className="border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas as filas</option>
            <option value="Raw">Raw</option>
            <option value="Junk">Junk</option>
            <option value="Misc">Misc</option>
          </select>
          <select
            value={state}
            onChange={(e) => setState(e.target.value)}
            className="border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos os estados</option>
            <option value="new">Novo</option>
            <option value="open">Aberto</option>
            <option value="closed successful">Fechado com sucesso</option>
            <option value="closed unsuccessful">Fechado sem sucesso</option>
          </select>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas prioridades</option>
            <option value="1 low">1 - Baixa</option>
            <option value="2 normal">2 - Normal</option>
            <option value="3 normal">3 - Normal</option>
            <option value="4 high">4 - Alta</option>
          </select>
          <Link
            to="/tickets/new"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-center"
          >
            Novo Ticket
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        {isLoading && (
          <div className="p-8 text-center text-gray-500">Carregando tickets...</div>
        )}
        {error && (
          <div className="p-8 text-center text-red-600">Erro ao carregar tickets</div>
        )}
        {!isLoading && !error && ticketIds.length === 0 && (
          <div className="p-8 text-center text-gray-500">Nenhum ticket encontrado</div>
        )}
        {ticketIds.length > 0 && (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">ID</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Acoes</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {ticketIds.map((ticketId: string) => (
                <tr key={ticketId} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-sm">#{ticketId}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/tickets/${ticketId}`}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        Ver detalhes
                      </Link>
                      {data?.TicketWebURLs?.find((t) => t.TicketID === ticketId)?.WebURL && (
                        <a
                          href={data.TicketWebURLs.find((t) => t.TicketID === ticketId)!.WebURL}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <ExternalLink size={14} />
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
