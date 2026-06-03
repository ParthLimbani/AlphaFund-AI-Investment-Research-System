const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export type AgentEvent = {
  node: string;
  label?: string;
  status: "complete" | "done" | "error";
  summary?: string;
  action?: string;
  confidence?: number;
  error?: string;
};

export type Decision = {
  id?: number;
  ticker: string;
  action: string;
  confidence: number;
  explanation: string;
  debate_winner?: string;
  risk_flag?: boolean;
  created_at: string;
};

export type Belief = {
  id?: number;
  ticker?: string;
  belief: string;
  relevant_agents: string[];
  created_at: string;
};

export async function startAnalysis(ticker: string, query = ""): Promise<{ session_id: string }> {
  const res = await fetch(`${BASE}/analyze/${ticker}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Failed to start analysis: ${res.statusText}`);
  return res.json();
}

export async function getResult(sessionId: string): Promise<{ status: string; data?: Record<string, unknown> }> {
  const res = await fetch(`${BASE}/result/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to get result: ${res.statusText}`);
  return res.json();
}

export function subscribeToStream(
  sessionId: string,
  onEvent: (e: AgentEvent) => void,
  onDone: () => void,
  onError: (err: string) => void
): () => void {
  const es = new EventSource(`${BASE}/stream/${sessionId}`);
  es.onmessage = (e) => {
    const data: AgentEvent = JSON.parse(e.data);
    if (data.node === "__done__") {
      onDone();
      es.close();
    } else if (data.node === "__error__") {
      onError(data.error || "Unknown error");
      es.close();
    } else {
      onEvent(data);
    }
  };
  es.onerror = () => {
    onError("Stream connection lost");
    es.close();
  };
  return () => es.close();
}

export async function getHistory(ticker?: string): Promise<Decision[]> {
  const url = ticker ? `${BASE}/history/${ticker}` : `${BASE}/history`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return data.decisions ?? [];
}

export type TickerSuggestion = { symbol: string; name: string; exchange: string };

export async function searchTickers(q: string): Promise<TickerSuggestion[]> {
  if (q.length < 1) return [];
  try {
    const res = await fetch(`${BASE}/search?q=${encodeURIComponent(q)}`);
    return res.ok ? res.json() : [];
  } catch {
    return [];
  }
}

export async function getMemory(ticker?: string): Promise<Belief[]> {
  const url = ticker ? `${BASE}/memory/${ticker}` : `${BASE}/memory`;
  const res = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return data.beliefs ?? [];
}
