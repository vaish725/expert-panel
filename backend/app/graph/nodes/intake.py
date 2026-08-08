"""Intake node: turns the user's raw submission into a structured DecisionState.

Uses a low-temperature structured-output call so implicit stakes and
constraints are surfaced for confirmation rather than silently assumed.
"""

from langchain_openai import ChatOpenAI

from app.config import settings
from app.graph.state import DecisionState
from app.models.schemas import IntakeExtraction

INTAKE_SYSTEM_PROMPT = """You are the intake stage of a structured decision-deliberation \
system. Given a user's decision question, options, and free-text context, restate the \
question clearly, confirm the options, and separately surface any stakes or constraints \
the user implied but did not say outright. Do not invent stakes that aren't reasonably \
implied by the text."""


def _build_intake_llm() -> ChatOpenAI:
    """Low temperature: consistency matters more than voice at this stage."""
    return ChatOpenAI(
        model=settings.structured_model,
        temperature=0,
        api_key=settings.openai_api_key,
    ).with_structured_output(IntakeExtraction)


async def intake_node(state: DecisionState) -> dict:
    """Parse the raw decision submission into structured fields.

    Expects `decision_question`, `options`, and `user_context` to already be
    present in state (populated from the API request body); fills in
    `min_rounds`/`max_rounds` defaults and resets the round counters.
    """
    llm = _build_intake_llm()
    raw_prompt = (
        f"Decision question: {state['decision_question']}\n"
        f"Proposed options: {', '.join(state['options'])}\n"
        f"User-supplied context: {state.get('user_context') or '(none provided)'}"
    )
    extraction: IntakeExtraction = await llm.ainvoke(
        [
            {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
            {"role": "user", "content": raw_prompt},
        ]
    )

    # implicit stakes/constraints are folded into user_context, clearly marked,
    # so personas see them but the user can review/edit them before round 1
    implied = []
    if extraction.implicit_stakes:
        implied.append("Implied stakes: " + "; ".join(extraction.implicit_stakes))
    if extraction.implicit_constraints:
        implied.append("Implied constraints: " + "; ".join(extraction.implicit_constraints))
    merged_context = state.get("user_context", "")
    if implied:
        merged_context = (merged_context + "\n" if merged_context else "") + "\n".join(implied)

    return {
        "decision_question": extraction.decision_question,
        "options": extraction.options,
        "user_context": merged_context,
        "evidence": [],
        "transcript": [],
        "claims_ledger": [],
        "round_number": 1,
        "min_rounds": state.get("min_rounds") or settings.min_rounds,
        "max_rounds": state.get("max_rounds") or settings.max_rounds,
        "new_claims_this_round": 0,
        "resolved_this_round": 0,
        "converged": False,
        "forced": False,
        "final_recommendation": None,
        "human_approved": False,
    }
