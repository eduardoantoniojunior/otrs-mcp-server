import type {
  Ticket,
  TicketSearchResult,
  TicketCreateInput,
  TicketUpdateInput,
  TicketHistory,
  ActivityResponse,
  ActivitySummary,
} from '../types/ticket';

const API_BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Erro na requisicao');
  }
  return response.json();
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  searchTickets: (params: {
    customer_user?: string;
    queue?: string;
    state?: string;
    priority?: string;
    title?: string;
    limit?: number;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        query.set(key, String(value));
      }
    });
    const qs = query.toString();
    return request<TicketSearchResult>(`/tickets${qs ? `?${qs}` : ''}`);
  },

  getTicket: (ticketId: string) =>
    request<Ticket>(`/tickets/${ticketId}`),

  createTicket: (data: TicketCreateInput) =>
    request<Ticket>('/tickets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateTicket: (ticketId: string, data: TicketUpdateInput) =>
    request<Ticket>(`/tickets/${ticketId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getTicketHistory: (ticketId: string) =>
    request<TicketHistory>(`/tickets/${ticketId}/history`),

  getActivity: (params: {
    limit?: number;
    tool?: string;
    status?: string;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        query.set(key, String(value));
      }
    });
    const qs = query.toString();
    return request<ActivityResponse>(`/activity${qs ? `?${qs}` : ''}`);
  },

  getActivitySummary: () =>
    request<ActivitySummary>('/activity/summary'),

  clearActivity: () =>
    request<{ status: string; message: string }>('/activity', {
      method: 'DELETE',
    }),
};
