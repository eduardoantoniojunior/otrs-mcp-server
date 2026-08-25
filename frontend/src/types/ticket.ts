export interface Ticket {
  TicketID: string;
  Title: string;
  State: string;
  Priority: string;
  Queue: string;
  Type?: string;
  CustomerUser?: string;
  Owner?: string;
  Created?: string;
  Changed?: string;
  WebURL?: string;
  HistoryWebURL?: string;
}

export interface TicketHistory {
  TicketID: string;
  History?: Array<{
    ArticleID?: string;
    Name?: string;
    CreateBy?: string;
    CreateTime?: string;
  }>;
  WebURL?: string;
  HistoryWebURL?: string;
}

export interface TicketSearchResult {
  TicketID?: string[];
  WebSearchURL?: string;
  TicketWebURLs?: Array<{
    TicketID: string;
    WebURL: string;
  }>;
}

export interface TicketCreateInput {
  title: string;
  body: string;
  queue?: string;
  priority?: string;
  state?: string;
  customer_user?: string;
  ticket_type?: string;
}

export interface TicketUpdateInput {
  title?: string;
  queue?: string;
  priority?: string;
  state?: string;
  customer_user?: string;
  owner?: string;
}

export interface ActivityEvent {
  tool: string;
  status: "success" | "error";
  duration_ms: number;
  timestamp: number;
  timestamp_iso: string;
  ticket_id?: string;
  error?: string;
  params?: Record<string, unknown>;
}

export interface ActivitySummary {
  total_calls: number;
  by_tool: Record<string, number>;
  by_status: { success: number; error: number };
  last_24h: {
    calls: number;
    by_tool: Record<string, number>;
  };
}

export interface ActivityResponse {
  events: ActivityEvent[];
  summary: ActivitySummary;
}
