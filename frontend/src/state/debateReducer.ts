// Single reducer all WS events and REST snapshots feed into, so token
// ordering stays consistent across panels (per PRD 11: one connection,
// reduced into local state, rather than each panel subscribing itself).

import { PERSONA_NAMES, nodeIdToPersona } from "../types/debate";
import type { Claim, DecisionState, PersonaName, ServerEvent, StructuredRecommendation, Turn } from "../types/debate";

export interface DebateUIState {
  threadId: string | null;
  decisionQuestion: string;
  options: string[];
  personaText: Record<PersonaName, string>;
  personaTyping: Record<PersonaName, boolean>;
  ledger: Claim[];
  roundNumber: number;
  minRounds: number;
  maxRounds: number;
  statusMessage: string;
  converged: boolean;
  forced: boolean;
  recommendation: StructuredRecommendation | null;
  exportedPath: string | null;
  error: string | null;
}

function emptyPersonaRecord<T>(value: T): Record<PersonaName, T> {
  return Object.fromEntries(PERSONA_NAMES.map((name) => [name, value])) as Record<PersonaName, T>;
}

export const initialDebateUIState: DebateUIState = {
  threadId: null,
  decisionQuestion: "",
  options: [],
  personaText: emptyPersonaRecord(""),
  personaTyping: emptyPersonaRecord(false),
  ledger: [],
  roundNumber: 1,
  minRounds: 2,
  maxRounds: 6,
  statusMessage: "Waiting for round 1...",
  converged: false,
  forced: false,
  recommendation: null,
  exportedPath: null,
  error: null,
};

export type DebateUIAction = { kind: "snapshot"; snapshot: DecisionState } | { kind: "server_event"; event: ServerEvent };

// on reconnect, seed each persona panel from its last completed turn in the
// current round; in-progress token deltas from before the disconnect are
// not recoverable, only whatever the transcript already has committed
function lastTurnByPersona(transcript: Turn[], round: number): Record<PersonaName, string> {
  const result = emptyPersonaRecord("");
  for (const turn of transcript) {
    const persona = turn.persona as PersonaName;
    if (turn.round === round && PERSONA_NAMES.includes(persona)) {
      result[persona] = turn.content;
    }
  }
  return result;
}

export function debateUIReducer(state: DebateUIState, action: DebateUIAction): DebateUIState {
  if (action.kind === "snapshot") {
    const snapshot = action.snapshot;
    return {
      ...state,
      threadId: snapshot.thread_id,
      decisionQuestion: snapshot.decision_question,
      options: snapshot.options,
      ledger: snapshot.claims_ledger,
      roundNumber: snapshot.round_number,
      minRounds: snapshot.min_rounds,
      maxRounds: snapshot.max_rounds,
      converged: snapshot.converged,
      forced: snapshot.forced,
      recommendation: snapshot.final_recommendation,
      exportedPath: snapshot.exported_report_path,
      personaText: lastTurnByPersona(snapshot.transcript, snapshot.round_number),
      statusMessage: snapshot.converged
        ? `Converged after round ${snapshot.round_number}${snapshot.forced ? " (forced)" : ""}`
        : `Round ${snapshot.round_number} in progress`,
    };
  }
  return applyServerEvent(state, action.event);
}

function applyServerEvent(state: DebateUIState, event: ServerEvent): DebateUIState {
  switch (event.type) {
    case "token": {
      const persona = nodeIdToPersona(event.node);
      if (!persona) return state;
      return {
        ...state,
        personaText: { ...state.personaText, [persona]: state.personaText[persona] + event.delta },
        personaTyping: { ...state.personaTyping, [persona]: true },
      };
    }
    case "claim_added": {
      if (state.ledger.some((c) => c.id === event.claim.id)) return state;
      return { ...state, ledger: [...state.ledger, event.claim] };
    }
    case "claim_resolved": {
      return {
        ...state,
        ledger: state.ledger.map((c) =>
          c.id === event.claim_id
            ? { ...c, contested: false, resolved_round: event.round, resolved_by: event.resolved_by }
            : c,
        ),
      };
    }
    case "round_complete": {
      return {
        ...state,
        roundNumber: event.converged ? event.round : event.round + 1,
        // only clear the panels when another round is actually about to
        // start; on the final round, leave the last turns visible instead
        // of blanking them out right as the recommendation appears
        personaText: event.converged ? state.personaText : emptyPersonaRecord(""),
        personaTyping: emptyPersonaRecord(false),
        statusMessage: event.converged
          ? `Round ${event.round}: no new ground, converging`
          : `Round ${event.round}: ${event.new_claims} new claim(s), ${event.resolved} resolved`,
      };
    }
    case "converged": {
      return {
        ...state,
        converged: true,
        forced: event.forced,
        statusMessage: event.forced
          ? `Converged after round ${event.round} (hit max rounds)`
          : `Converged after round ${event.round}`,
      };
    }
    case "recommendation_ready":
      return { ...state, recommendation: event.recommendation };
    case "exported":
      return { ...state, exportedPath: event.path };
    case "error":
      return { ...state, error: event.message };
    default:
      return state;
  }
}
