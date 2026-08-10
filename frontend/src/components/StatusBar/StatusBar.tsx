// Current round number, min/max rounds, and a convergence indicator that
// visibly changes state on round_complete (PRD 11).

import "./StatusBar.css";

interface StatusBarProps {
  decisionQuestion: string;
  roundNumber: number;
  minRounds: number;
  maxRounds: number;
  converged: boolean;
  forced: boolean;
  statusMessage: string;
}

export function StatusBar({
  decisionQuestion,
  roundNumber,
  minRounds,
  maxRounds,
  converged,
  forced,
  statusMessage,
}: StatusBarProps) {
  return (
    <div className="status-bar">
      <div className="status-bar__question">{decisionQuestion}</div>
      <div className="status-bar__meta">
        <span>
          round {roundNumber} / {maxRounds} (min {minRounds})
        </span>
        <span className={`status-bar__indicator ${converged ? (forced ? "status-bar__indicator--forced" : "status-bar__indicator--converged") : ""}`}>
          {statusMessage}
        </span>
      </div>
    </div>
  );
}
