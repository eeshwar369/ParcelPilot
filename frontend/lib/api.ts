export type User = {
  user_id: string;
  display_name: string;
  role: string;
  account_id: string | null;
};

export type ChatResponse = {
  answer: string;
  confidence: "high" | "medium" | "low";
  sources: Array<Record<string, unknown>>;
  tool_trace: Array<Record<string, unknown>>;
  model_trace: Array<Record<string, unknown>>;
  pending_action?: Record<string, unknown> | null;
  error?: string;
};

export type EscalationQueue = {
  escalations: Array<Record<string, any> & { response?: string }>;
  pending_actions: Array<Record<string, any>>;
};

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL || API_BASE.replace(/^http/, "ws");

export async function apiGet<T>(path: string, userId?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: userId ? { "X-User-Id": userId } : undefined,
    cache: "no-store"
  });
  return response.json();
}

export async function apiPost<T>(path: string, body: unknown, userId?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(userId ? { "X-User-Id": userId } : {})
    },
    body: JSON.stringify(body)
  });
  return response.json();
}
