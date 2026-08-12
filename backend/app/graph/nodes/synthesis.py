"""Synthesis node: turns the full claims ledger into a StructuredRecommendation.

Runs once, after convergence, and consumes the whole ledger (not just the
transcript) so the recommendation is traceable back to specific claim ids.
"""

from langchain_anthropic import ChatAnthropic
from langgraph.config import get_stream_writer

from app.config import settings
from app.graph.ledger import render_ledger
from app.graph.state import DecisionState, StructuredRecommendation
from app.models.schemas import SynthesisOutput

SYNTHESIS_SYSTEM_PROMPT = """You synthesize a structured decision debate into a final \
recommendation. You will see the full claims ledger: every argument raised, whether it is \
still contested or was resolved. Base recommended_option on the weight of resolved and \
well-supported claims. If the ledger is genuinely balanced between options, set \
recommended_option to null and explain why in confidence_note. Every tradeoff entry must \
cite a real claim id from the ledger, never an invented one."""


def _build_synthesis_llm() -> ChatAnthropic:
    # no explicit temperature: this model rejects the parameter outright
    return ChatAnthropic(
        model=settings.structured_model,
        api_key=settings.anthropic_api_key,
    ).with_structured_output(SynthesisOutput)


async def synthesize_node(state: DecisionState) -> dict:
    """Produce the final recommendation and persist it to state for human review."""
    llm = _build_synthesis_llm()
    prompt = (
        f"Decision: {state['decision_question']}\n"
        f"Options: {', '.join(state['options'])}\n"
        f"Forced convergence (hit max_rounds while the debate was still productive): {state['forced']}\n\n"
        f"Full claims ledger:\n{render_ledger(state['claims_ledger'])}"
    )
    output: SynthesisOutput = await llm.ainvoke(
        [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    # derived directly from the ledger, not left to the model to recall
    unresolved_disagreements = [c["id"] for c in state["claims_ledger"] if c["contested"]]

    # group the model's flat tradeoff list back into the per-option shape
    # the rest of the app (state schema, report, frontend) expects
    tradeoffs_by_option: dict[str, list[dict]] = {option: [] for option in state["options"]}
    for item in output.tradeoffs:
        tradeoffs_by_option.setdefault(item.option, []).append({"claim_id": item.claim_id, "direction": item.direction})

    recommendation: StructuredRecommendation = {
        "recommended_option": output.recommended_option,
        "tradeoffs": tradeoffs_by_option,
        "unresolved_disagreements": unresolved_disagreements,
        "confidence_note": output.confidence_note,
    }

    writer = get_stream_writer()
    writer({"type": "recommendation_ready", "recommendation": dict(recommendation)})

    return {"final_recommendation": recommendation}
