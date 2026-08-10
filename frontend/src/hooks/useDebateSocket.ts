// Owns the single WebSocket connection for one debate: fetches the latest
// snapshot on connect/reconnect (PRD 11 reconnect logic), then reduces live
// events into local state, and exposes the 3 review actions the client can
// send back.

import { useCallback, useEffect, useReducer, useRef } from "react";
import { debateStreamUrl, fetchDebateSnapshot } from "../api";
import { debateUIReducer, initialDebateUIState } from "../state/debateReducer";
import type { ClientEvent, ServerEvent, StructuredRecommendation } from "../types/debate";

export function useDebateSocket(threadId: string | null) {
  const [state, dispatch] = useReducer(debateUIReducer, initialDebateUIState);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!threadId) return;
    let cancelled = false;

    (async () => {
      try {
        const snapshot = await fetchDebateSnapshot(threadId);
        if (!cancelled) dispatch({ kind: "snapshot", snapshot });
      } catch {
        // no checkpoint written yet (debate just started); the WS stream
        // below still populates everything live from round 1
      }

      const socket = new WebSocket(debateStreamUrl(threadId));
      socketRef.current = socket;
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as ServerEvent;
        dispatch({ kind: "server_event", event });
      };
    })();

    return () => {
      cancelled = true;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [threadId]);

  const send = useCallback((event: ClientEvent) => {
    socketRef.current?.send(JSON.stringify(event));
  }, []);

  const approve = useCallback(() => send({ type: "approve" }), [send]);
  const edit = useCallback(
    (recommendation: StructuredRecommendation) => send({ type: "edit", recommendation }),
    [send],
  );
  const reopen = useCallback(
    (followUpQuestion: string) => send({ type: "reopen", follow_up_question: followUpQuestion }),
    [send],
  );

  return { state, approve, edit, reopen };
}
