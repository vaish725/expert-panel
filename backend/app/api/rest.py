"""REST endpoints: start a debate, fetch its current snapshot, and resume it
past the human-review gate. The WebSocket endpoint (app/api/websocket.py)
handles the live event stream; these routes handle request/response only.
"""

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import ResumeRequest, StartDebateRequest, StartDebateResponse
from app.graph.personas.prompts import PERSONAS
from app.graph.state import DecisionState

router = APIRouter(prefix="/debates", tags=["debates"])


def _build_initial_state(thread_id: str, request: StartDebateRequest) -> DecisionState:
    """Seed a fresh DecisionState; the intake node fills in the rest
    (parsed question/options, implicit stakes folded into context, counters)."""
    return {
        "thread_id": thread_id,
        "decision_question": request.decision_question,
        "options": request.options,
        "user_context": request.context,
        "evidence": [],
        "personas": PERSONAS,
        "transcript": [],
        "claims_ledger": [],
        "round_number": 1,
        "min_rounds": request.min_rounds,
        "max_rounds": request.max_rounds,
        "new_claims_this_round": 0,
        "resolved_this_round": 0,
        "converged": False,
        "forced": False,
        "final_recommendation": None,
        "human_approved": False,
        "exported_report_path": None,
    }


@router.post("", response_model=StartDebateResponse)
async def start_debate(request: StartDebateRequest, http_request: Request) -> StartDebateResponse:
    thread_id = str(uuid.uuid4())
    initial_state = _build_initial_state(thread_id, request)
    http_request.app.state.manager.start(initial_state)
    return StartDebateResponse(thread_id=thread_id)


@router.get("/{thread_id}")
async def get_debate(thread_id: str, http_request: Request) -> dict:
    snapshot = await http_request.app.state.manager.get_snapshot(thread_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="debate not found")
    return snapshot


@router.post("/{thread_id}/resume")
async def resume_debate(thread_id: str, request: ResumeRequest, http_request: Request) -> dict:
    manager = http_request.app.state.manager
    if request.action in ("approve", "edit"):
        edits = request.payload if request.action == "edit" else None
        await manager.resume_approve(thread_id, recommendation_edits=edits)
    elif request.action == "reopen":
        follow_up = (request.payload or {}).get("follow_up_question", "")
        await manager.reopen(thread_id, follow_up)
    return {"status": "ok"}
