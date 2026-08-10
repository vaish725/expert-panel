"""Runs debates as background tasks and fans out their live custom events to
any number of subscribed WebSocket connections.

Every node-level event (token, claim_added, claim_resolved, round_complete,
converged, recommendation_ready, exported) is dispatched via
get_stream_writer() inside the graph nodes; this manager just relays those
dicts verbatim to subscribers, since they already match the WS wire schema.
"""

import asyncio
import logging

from app.graph.state import DecisionState

logger = logging.getLogger(__name__)


class DebateManager:
    def __init__(self, graph):
        self._graph = graph
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    def _config(self, thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

    def subscribe(self, thread_id: str) -> asyncio.Queue:
        """Register a new WS connection as a listener for this thread's events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(thread_id, []).append(queue)
        return queue

    def unsubscribe(self, thread_id: str, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(thread_id, [])
        if queue in subs:
            subs.remove(queue)

    async def _broadcast(self, thread_id: str, message: dict) -> None:
        for queue in self._subscribers.get(thread_id, []):
            await queue.put(message)

    async def _stream(self, thread_id: str, input_state) -> None:
        """Run (or resume) the graph, relaying every custom event as it's
        emitted. input_state is the initial DecisionState to start a new
        debate, or None to resume a paused one."""
        config = self._config(thread_id)
        try:
            async for event in self._graph.astream(input_state, config, stream_mode="custom"):
                await self._broadcast(thread_id, event)
        except Exception as exc:  # noqa: BLE001 - surface any failure to connected clients
            logger.exception("debate %s failed", thread_id)
            await self._broadcast(thread_id, {"type": "error", "message": str(exc)})

    def start(self, initial_state: DecisionState) -> None:
        """Kick off a new debate as a detached background task."""
        asyncio.create_task(self._stream(initial_state["thread_id"], initial_state))

    async def resume_approve(self, thread_id: str, recommendation_edits: dict | None = None) -> None:
        """Approve (optionally with edited recommendation fields) and resume
        past the interrupt_before("export") gate."""
        values: dict = {"human_approved": True}
        if recommendation_edits is not None:
            values["final_recommendation"] = recommendation_edits
        await self._graph.aupdate_state(self._config(thread_id), values)
        asyncio.create_task(self._stream(thread_id, None))

    async def reopen(self, thread_id: str, follow_up_question: str) -> None:
        """Force one more debate round with a follow-up question, without
        resetting the ledger or already-tracked claims (PRD 5.7)."""
        snapshot = await self._graph.aget_state(self._config(thread_id))
        state = snapshot.values
        appended_context = state.get("user_context", "")
        if follow_up_question:
            appended_context = (appended_context + "\n" if appended_context else "") + f"Follow-up question: {follow_up_question}"

        values = {
            "max_rounds": state["max_rounds"] + 1,
            "converged": False,
            "forced": False,
            "user_context": appended_context,
        }
        # writes this update as if it came from check_convergence, so resuming
        # follows that node's normal outgoing edge back to the 4 personas
        await self._graph.aupdate_state(self._config(thread_id), values, as_node="check_convergence")
        asyncio.create_task(self._stream(thread_id, None))

    async def get_snapshot(self, thread_id: str) -> dict | None:
        snapshot = await self._graph.aget_state(self._config(thread_id))
        return snapshot.values or None
