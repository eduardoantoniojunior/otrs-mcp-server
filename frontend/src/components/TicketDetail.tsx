import { useParams, Link } from 'react-router-dom';
import { useTicket, useTicketHistory } from '../hooks/useTickets';
import { ArrowLeft, ExternalLink, Clock } from 'lucide-react';

export default function TicketDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: ticket, isLoading, error } = useTicket(id ?? '');
  const { data: history } = useTicketHistory(id ?? '');

  if (isLoading) {
    return <div className="text-gray-500">Carregando ticket...</div>;
  }

  if (error || !ticket) {
    return <div className="text-red-600">Erro ao carregar ticket</div>;
  }

  const historyItems = history?.History ?? [];

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link to="/tickets" className="text-gray-500 hover:text-gray-700">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold">Ticket #{id}</h1>
        <Link
          to={`/tickets/${id}/edit`}
          className="ml-auto bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors text-sm"
        >
          Editar
        </Link>
        {ticket.WebURL && (
          <a
            href={ticket.WebURL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline text-sm"
          >
            Abrir no OTRS <ExternalLink size={14} />
          </a>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">{ticket.Title}</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">ID:</span>
                <span className="ml-2 font-mono">{ticket.TicketID}</span>
              </div>
              <div>
                <span className="text-gray-500">Fila:</span>
                <span className="ml-2">{ticket.Queue}</span>
              </div>
              <div>
                <span className="text-gray-500">Estado:</span>
                <span className="ml-2">{ticket.State}</span>
              </div>
              <div>
                <span className="text-gray-500">Prioridade:</span>
                <span className="ml-2">{ticket.Priority}</span>
              </div>
              {ticket.CustomerUser && (
                <div>
                  <span className="text-gray-500">Cliente:</span>
                  <span className="ml-2">{ticket.CustomerUser}</span>
                </div>
              )}
              {ticket.Owner && (
                <div>
                  <span className="text-gray-500">Responsavel:</span>
                  <span className="ml-2">{ticket.Owner}</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Clock size={18} />
              Historico
            </h2>
            {historyItems.length === 0 ? (
              <p className="text-gray-500">Nenhum historico encontrado</p>
            ) : (
              <div className="space-y-3">
                {historyItems.map((item, index) => (
                  <div key={index} className="flex items-start gap-3 text-sm">
                    <div className="w-2 h-2 mt-2 rounded-full bg-blue-500 flex-shrink-0" />
                    <div>
                      <p>{item.Name}</p>
                      <p className="text-gray-400 text-xs">
                        {item.CreateBy} - {item.CreateTime}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Informacoes</h2>
            <dl className="space-y-3 text-sm">
              {ticket.Created && (
                <>
                  <dt className="text-gray-500">Criado em</dt>
                  <dd>{ticket.Created}</dd>
                </>
              )}
              {ticket.Changed && (
                <>
                  <dt className="text-gray-500">Ultima alteracao</dt>
                  <dd>{ticket.Changed}</dd>
                </>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
