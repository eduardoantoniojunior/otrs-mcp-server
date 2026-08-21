import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTicket, useCreateTicket, useUpdateTicket } from '../hooks/useTickets';
import { ArrowLeft } from 'lucide-react';

export default function TicketForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const { data: existingTicket } = useTicket(id ?? '');
  const createTicket = useCreateTicket();
  const updateTicket = useUpdateTicket();

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [queue, setQueue] = useState('Raw');
  const [priority, setPriority] = useState('3 normal');
  const [state, setState] = useState('new');
  const [customerUser, setCustomerUser] = useState('');

  useEffect(() => {
    if (existingTicket && isEditing) {
      setTitle(existingTicket.Title ?? '');
      setQueue(existingTicket.Queue ?? 'Raw');
      setPriority(existingTicket.Priority ?? '3 normal');
      setState(existingTicket.State ?? 'new');
      setCustomerUser(existingTicket.CustomerUser ?? '');
    }
  }, [existingTicket, isEditing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditing && id) {
        await updateTicket.mutateAsync({
          ticketId: id,
          data: { title, queue, priority, state, customer_user: customerUser || undefined },
        });
        navigate(`/tickets/${id}`);
      } else {
        const result = await createTicket.mutateAsync({
          title,
          body,
          queue,
          priority,
          state,
          customer_user: customerUser || undefined,
        });
        navigate(`/tickets/${result.TicketID}`);
      }
    } catch {
      // Error handled by mutation
    }
  };

  const isPending = createTicket.isPending || updateTicket.isPending;

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link to={isEditing ? `/tickets/${id}` : '/tickets'} className="text-gray-500 hover:text-gray-700">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold">{isEditing ? 'Editar Ticket' : 'Novo Ticket'}</h1>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 max-w-2xl">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Titulo *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Corpo *</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
                rows={5}
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fila</label>
              <select
                value={queue}
                onChange={(e) => setQueue(e.target.value)}
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Raw">Raw</option>
                <option value="Junk">Junk</option>
                <option value="Misc">Misc</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prioridade</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="1 very low">1 - Muito Baixa</option>
                <option value="2 low">2 - Baixa</option>
                <option value="3 normal">3 - Normal</option>
                <option value="4 high">4 - Alta</option>
                <option value="5 very high">5 - Muito Alta</option>
              </select>
            </div>
          </div>

          {isEditing && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                <select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="new">Novo</option>
                  <option value="open">Aberto</option>
                  <option value="closed successful">Fechado com sucesso</option>
                  <option value="closed unsuccessful">Fechado sem sucesso</option>
                </select>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cliente (email)</label>
            <input
              type="text"
              value={customerUser}
              onChange={(e) => setCustomerUser(e.target.value)}
              placeholder="opcional"
              className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {(createTicket.isError || updateTicket.isError) && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            Erro ao {isEditing ? 'atualizar' : 'criar'} ticket. Tente novamente.
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <button
            type="submit"
            disabled={isPending}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {isPending ? 'Salvando...' : isEditing ? 'Salvar' : 'Criar Ticket'}
          </button>
          <Link
            to={isEditing ? `/tickets/${id}` : '/tickets'}
            className="bg-gray-200 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
