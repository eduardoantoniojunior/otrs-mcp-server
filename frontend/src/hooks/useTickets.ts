import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { TicketCreateInput, TicketUpdateInput } from '../types/ticket';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
    retry: 3,
  });
}

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => api.getConfig(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

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

export function useActivity(params: {
  limit?: number;
  tool?: string;
  status?: string;
} = {}) {
  return useQuery({
    queryKey: ['activity', params],
    queryFn: () => api.getActivity(params),
    refetchInterval: 10000,
  });
}

export function useActivitySummary() {
  return useQuery({
    queryKey: ['activitySummary'],
    queryFn: () => api.getActivitySummary(),
    refetchInterval: 10000,
  });
}

export function useClearActivity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.clearActivity(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activity'] });
      queryClient.invalidateQueries({ queryKey: ['activitySummary'] });
    },
  });
}
