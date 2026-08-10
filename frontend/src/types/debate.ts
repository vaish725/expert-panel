// Mirrors the backend's DecisionState and WS message schema
// (backend/app/graph/state.py, backend/app/api/websocket.py).

export interface Claim {
  id: string;
  text: string;
  raised_by: string;
  round_introduced: number;
  stance: string;
  contested: boolean;
  reinforced_count: number;
  resolved_round: number | null;
  resolved_by: string | null;
}

export interface Turn {
  round: number;
  persona: string;
  content: string;
}

export interface TradeoffItem {
  claim_id: string;
  direction: "pro" | "con";
}

export interface StructuredRecommendation {
  recommended_option: string | null;
  tradeoffs: Record<string, TradeoffItem[]>;
  unresolved_disagreements: string[];
  confidence_note: string;
}

export interface EvidenceItem {
  source: string;
  snippet: string;
  url: string;
}

export interface DecisionState {
  thread_id: string;
  decision_question: string;
  options: string[];
  user_context: string;
  evidence: EvidenceItem[];
  transcript: Turn[];
  claims_ledger: Claim[];
  round_number: number;
  min_rounds: number;
  max_rounds: number;
  converged: boolean;
  forced: boolean;
  final_recommendation: StructuredRecommendation | null;
  human_approved: boolean;
  exported_report_path: string | null;
}

export const PERSONA_NAMES = ["skeptic", "optimist", "contrarian", "pragmatist"] as const;
export type PersonaName = (typeof PERSONA_NAMES)[number];

export function nodeIdToPersona(nodeId: string): PersonaName | null {
  const name = nodeId.replace(/^persona_/, "");
  return (PERSONA_NAMES as readonly string[]).includes(name) ? (name as PersonaName) : null;
}

// server -> client
export type ServerEvent =
  | { type: "token"; node: string; round: number; delta: string }
  | { type: "claim_added"; claim: Claim }
  | { type: "claim_resolved"; claim_id: string; resolved_by: string; round: number }
  | { type: "round_complete"; round: number; new_claims: number; resolved: number; converged: boolean }
  | { type: "converged"; round: number; forced: boolean }
  | { type: "recommendation_ready"; recommendation: StructuredRecommendation }
  | { type: "exported"; path: string }
  | { type: "error"; message: string };

// client -> server
export type ClientEvent =
  | { type: "approve" }
  | { type: "edit"; recommendation: StructuredRecommendation }
  | { type: "reopen"; follow_up_question: string };
