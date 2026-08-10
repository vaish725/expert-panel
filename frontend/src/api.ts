// Thin REST client for the FastAPI backend. The live event stream itself
// goes over WebSocket (see hooks/useDebateSocket.ts); this only covers
// starting a debate and fetching a snapshot on connect/reconnect.

import type { DecisionState } from "./types/debate";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface StartDebatePayload {
  decision_question: string;
  options: string[];
  context: string;
  min_rounds: number;
  max_rounds: number;
}

export async function startDebate(payload: StartDebatePayload): Promise<{ thread_id: string }> {
  const res = await fetch(`${API_BASE}/debates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`failed to start debate (${res.status})`);
  return res.json();
}

export async function fetchDebateSnapshot(threadId: string): Promise<DecisionState> {
  const res = await fetch(`${API_BASE}/debates/${threadId}`);
  if (!res.ok) throw new Error(`failed to fetch debate (${res.status})`);
  return res.json();
}

export function debateStreamUrl(threadId: string): string {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/debates/${threadId}/stream`;
}
