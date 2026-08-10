// Top-level wiring: intake form until a debate exists, then the live
// debate view driven by the single WebSocket connection (PRD 11).

import { useEffect, useState } from "react";
import { DebateView } from "./components/DebateView/DebateView";
import { IntakeForm } from "./components/IntakeForm";
import { Ledger } from "./components/Ledger/Ledger";
import { ReviewPanel } from "./components/ReviewPanel/ReviewPanel";
import { StatusBar } from "./components/StatusBar/StatusBar";
import { useDebateSocket } from "./hooks/useDebateSocket";

const THREAD_STORAGE_KEY = "expert-panel:thread-id";

export default function App() {
  const [threadId, setThreadId] = useState<string | null>(() => localStorage.getItem(THREAD_STORAGE_KEY));

  useEffect(() => {
    if (threadId) localStorage.setItem(THREAD_STORAGE_KEY, threadId);
  }, [threadId]);

  function startNewDebate() {
    localStorage.removeItem(THREAD_STORAGE_KEY);
    setThreadId(null);
  }

  if (!threadId) {
    return <IntakeForm onStarted={setThreadId} />;
  }

  return <DebateScreen threadId={threadId} onNewDebate={startNewDebate} />;
}

function DebateScreen({ threadId, onNewDebate }: { threadId: string; onNewDebate: () => void }) {
  const { state, approve, edit, reopen } = useDebateSocket(threadId);

  return (
    <div className="app-shell">
      <StatusBar
        decisionQuestion={state.decisionQuestion}
        roundNumber={state.roundNumber}
        minRounds={state.minRounds}
        maxRounds={state.maxRounds}
        converged={state.converged}
        forced={state.forced}
        statusMessage={state.statusMessage}
      />

      {state.error && <p className="app-shell__error">{state.error}</p>}

      <div className="app-shell__body">
        <DebateView personaText={state.personaText} personaTyping={state.personaTyping} roundNumber={state.roundNumber} />
        <Ledger claims={state.ledger} />
      </div>

      {state.recommendation && (
        <ReviewPanel
          recommendation={state.recommendation}
          options={state.options}
          exportedPath={state.exportedPath}
          onApprove={approve}
          onEdit={edit}
          onReopen={reopen}
        />
      )}

      <button className="app-shell__new-debate" onClick={onNewDebate}>
        Start a new debate
      </button>
    </div>
  );
}
