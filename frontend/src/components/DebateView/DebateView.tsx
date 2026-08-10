// 2x2 grid, one panel per persona, each rendering its streamed text live as
// token events arrive for its node tag (PRD 11).

import { PERSONA_NAMES } from "../../types/debate";
import type { PersonaName } from "../../types/debate";
import "./DebateView.css";

interface DebateViewProps {
  personaText: Record<PersonaName, string>;
  personaTyping: Record<PersonaName, boolean>;
  roundNumber: number;
}

export function DebateView({ personaText, personaTyping, roundNumber }: DebateViewProps) {
  return (
    <div className="debate-view">
      {PERSONA_NAMES.map((persona) => (
        <PersonaPanel
          key={persona}
          persona={persona}
          text={personaText[persona]}
          typing={personaTyping[persona]}
          roundNumber={roundNumber}
        />
      ))}
    </div>
  );
}

function PersonaPanel({
  persona,
  text,
  typing,
  roundNumber,
}: {
  persona: PersonaName;
  text: string;
  typing: boolean;
  roundNumber: number;
}) {
  return (
    <div className={`persona-panel persona-panel--${persona}`}>
      <div className="persona-panel__header">
        <span className="persona-panel__name">{persona}</span>
        <span className="persona-panel__round">round {roundNumber}</span>
        {typing && <span className="persona-panel__typing">typing...</span>}
      </div>
      <div className="persona-panel__body">{text || <span className="persona-panel__empty">Waiting...</span>}</div>
    </div>
  );
}
