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
    let closed = false;
    let snapshotApplied = false;
    const buffered: ServerEvent[] = [];

    // the socket is created synchronously (not after an awaited fetch), so
    // cleanup can always close it deterministically; if it were created
    // after an await, a re-run of this effect (StrictMode double-invoke in
    // dev, or any legitimate remount) could leave two live connections,
    // since cleanup would run before socketRef.current was ever assigned
    const socket = new WebSocket(debateStreamUrl(threadId));
    socketRef.current = socket;

    // buffer live events until the snapshot baseline is applied, so a
    // slow snapshot fetch can never overwrite state a live event already
    // advanced past
    socket.onmessage = (message) => {
      if (closed) return;
      const event = JSON.parse(message.data) as ServerEvent;
      if (!snapshotApplied) {
        buffered.push(event);
        return;
      }
      dispatch({ kind: "server_event", event });
    };

    fetchDebateSnapshot(threadId)
      .then((snapshot) => {
        if (!closed) dispatch({ kind: "snapshot", snapshot });
      })
      .catch(() => {
        // no checkpoint written yet (debate just started); live events
        // populate everything from round 1 regardless
      })
      .finally(() => {
        if (closed) return;
        snapshotApplied = true;
        for (const event of buffered) dispatch({ kind: "server_event", event });
        buffered.length = 0;
      });

    return () => {
      closed = true;
      socket.close();
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
