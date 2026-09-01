import type {
  Ticket,
  TicketSearchResult,
  TicketCreateInput,
  TicketUpdateInput,
  TicketHistory,
  ActivityResponse,
  ActivitySummary,
} from '../types/ticket';

// API_BASE respeita o subpath configurado via VITE_BASE_PATH
// Sem subpath: BASE_URL="/" → API_BASE="/api"
// Com subpath: BASE_URL="/otrs/" → API_BASE="/otrs/api"
const _base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');
const API_BASE = `${_base}/api`;
const REQUEST_TIMEOUT_MS = 30_000;

// Callback de logout — injetado pelo AuthContext para evitar acoplamento
let _onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(callback: () => void) {
  _onUnauthorized = callback;
}

function getToken(): string | null {
  return localStorage.getItem('otrs_token');
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Timeout via AbortController
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (response.status === 401) {
      // Usar callback centralizado em vez de window.location
      if (_onUnauthorized) {
        _onUnauthorized();
      }
      throw new Error('Sessao expirada');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Erro na requisicao');
    }
    return response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Tempo limite da requisicao excedido');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  
  getConfig: () => request<{ valid_queues: string[]; valid_types: string[] }>('/config'),

  // Tickets
  searchTickets: (params: {
    customer_user?: string;
    customer_id?: string;
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

  // Activity (requires auth)
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

  // Admin - API Keys
  listApiKeys: (includeInactive = false) =>
    request<Array<{
      id: number;
      name: string;
      key_prefix: string;
      agent_name: string;
      permissions: string[];
      rate_limit: number;
      active: boolean;
      usage_count: number;
      last_used_at: string | null;
      created_at: string;
      expires_at: string | null;
    }>>(`/admin/keys?include_inactive=${includeInactive}`),

  createApiKey: (data: {
    name: string;
    agent_name: string;
    permissions?: string[];
    rate_limit?: number;
    expires_in_days?: number;
  }) =>
    request<{
      id: number;
      key: string;
      key_prefix: string;
      name: string;
      agent_name: string;
    }>('/admin/keys', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  revokeApiKey: (id: number) =>
    request<{ status: string; message: string }>(`/admin/keys/${id}/revoke`, {
      method: 'PATCH',
    }),

  deleteApiKey: (id: number) =>
    request<{ status: string; message: string }>(`/admin/keys/${id}`, {
      method: 'DELETE',
    }),

  // Admin - Users
  listUsers: () =>
    request<Array<{ id: number; username: string; active: boolean; created_at: string }>>(
      '/admin/users'
    ),

  createUser: (data: { username: string; password: string }) =>
    request<{ id: number; username: string }>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteUser: (id: number) =>
    request<{ status: string; message: string }>(`/admin/users/${id}`, {
      method: 'DELETE',
    }),

  // Admin - Activity Log (detailed)
  getAdminActivity: (params: {
    limit?: number;
    tool?: string;
    status?: string;
    agent?: string;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        query.set(key, String(value));
      }
    });
    const qs = query.toString();
    return request<{
      events: Array<{
        id: number;
        api_key_id: number | null;
        agent_name: string | null;
        tool: string;
        status: string;
        duration_ms: number;
        params: Record<string, unknown> | null;
        error: string | null;
        ticket_id: string | null;
        created_at: string;
      }>;
      summary: {
        total: number;
        success_count: number;
        error_count: number;
      };
    }>(`/admin/activity${qs ? `?${qs}` : ''}`);
  },

  // Admin - Login Audit
  getLoginAudit: (params: {
    limit?: number;
    username?: string;
    success?: boolean;
  } = {}) => {
    const query = new URLSearchParams();
    if (params.limit) query.set('limit', String(params.limit));
    if (params.username) query.set('username', params.username);
    if (params.success !== undefined) query.set('success', String(params.success));
    const qs = query.toString();
    return request<Array<{
      id: number;
      username: string;
      success: boolean;
      ip_address: string | null;
      user_agent: string | null;
      created_at: string;
    }>>(`/admin/login-audit${qs ? `?${qs}` : ''}`);
  },

  // Admin - Daily Metrics (charts)
  getDailyMetrics: (days: number = 14) =>
    request<{
      days: Array<{ date: string; total: number; success: number; errors: number }>;
      top_agents: Array<{ agent_name: string; total: number }>;
      by_tool: Array<{ tool: string; total: number; success: number; errors: number }>;
    }>(`/admin/metrics/daily?days=${days}`),
};
