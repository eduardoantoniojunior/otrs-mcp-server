import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { TicketCreateInput, TicketUpdateInput } from '../types/ticket';

export function useTickets(params: {
  customer_user?: string;
  queue?: string;
  state?: string;
  priority?: string;
  title?: string;
  limit?: number;
} = {}) {
  return useQuery({
    queryKey: ['tickets', params],
    queryFn: () => api.searchTickets(params),
  });
}

export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: ['ticket', ticketId],
    queryFn: () => api.getTicket(ticketId),
    enabled: !!ticketId,
  });
}

export function useTicketHistory(ticketId: string) {
  return useQuery({
    queryKey: ['ticketHistory', ticketId],
    queryFn: () => api.getTicketHistory(ticketId),
    enabled: !!ticketId,
  });
}

export function useCreateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TicketCreateInput) => api.createTicket(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useUpdateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ticketId, data }: { ticketId: string; data: TicketUpdateInput }) =>
      api.updateTicket(ticketId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['ticket', variables.ticketId] });
    },
  });
}
