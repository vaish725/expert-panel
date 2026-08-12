"""Claim extraction node: runs after each round's 4 persona turns complete.

Classifies every distinct assertion as a new claim, a restatement of an
existing one, or a resolution of one. This is an LLM call with structured
output (not string similarity) so paraphrases are recognized correctly.
"""

from langchain_anthropic import ChatAnthropic
from langgraph.config import get_stream_writer

from app.config import settings
from app.graph.ledger import render_ledger
from app.graph.state import Claim, DecisionState
from app.models.schemas import RoundExtraction

EXTRACTION_SYSTEM_PROMPT = """You classify arguments raised in one round of a structured \
decision debate. You will see the existing claims ledger and this round's persona turns. \
For every distinct assertion in this round's turns, decide if it is:
- "new": an assertion not already covered by the ledger.
- "restatement": the same point as an existing claim, just paraphrased or reinforced.
- "resolution": this turn concedes, settles, or resolves an existing contested claim.
Recognize paraphrases as restatements/resolutions rather than filing them as new claims. \
For "restatement" and "resolution", you must set target_claim_id to an existing ledger id."""


def _build_extraction_llm():
    # no explicit temperature: this model rejects the parameter outright;
    # low-variance classification is the point of structured output anyway.
    # with_retry guards against occasional malformed tool-call output on
    # this schema (see synthesis.py for the failure mode this catches).
    return (
        ChatAnthropic(
            model=settings.structured_model,
            api_key=settings.anthropic_api_key,
        )
        .with_structured_output(RoundExtraction)
        .with_retry(stop_after_attempt=3)
    )


def _render_round_turns(transcript: list, round_number: int) -> str:
    turns = [t for t in transcript if t["round"] == round_number]
    return "\n\n".join(f"{t['persona']}:\n{t['content']}" for t in turns)


def normalize_stance(raw_stance: str, options: list[str]) -> str:
    """Match the model's freeform stance text to one of the decision's exact
    option strings, or "neutral" if none matches.

    The model is only prompted to name "which option" a claim favors, not to
    echo the option string verbatim, so it may return a different casing or
    a shortened paraphrase (e.g. "adopt prettier" for "Adopt Prettier").
    Downstream code (synthesis's tradeoffs table) matches stance against
    state["options"] by exact string, so this normalization is required for
    a claim to ever show up under its option there.
    """
    normalized = raw_stance.strip().lower()
    if normalized == "neutral":
        return "neutral"
    for option in options:
        if normalized == option.lower():
            return option
    for option in options:
        if normalized in option.lower() or option.lower() in normalized:
            return option

    # word-overlap fallback: a shortened paraphrase ("keep manual" for "Keep
    # formatting manually") may share no full substring with the option, but
    # shares most of its significant words
    stop_words = {"the", "a", "an", "to", "of", "for", "and", "or"}
    raw_words = {w for w in normalized.split() if w not in stop_words}
    best_option, best_overlap = None, 0
    for option in options:
        option_words = {w for w in option.lower().split() if w not in stop_words}
        overlap = sum(1 for rw in raw_words if any(rw in ow or ow in rw for ow in option_words))
        if overlap > best_overlap:
            best_option, best_overlap = option, overlap
    return best_option or "neutral"


async def extract_claims_node(state: DecisionState) -> dict:
    """Process this round's persona turns against the ledger and return the
    updated ledger plus this round's new/resolved counts (used by convergence)."""
    llm = _build_extraction_llm()
    prompt = (
        f"Existing claims ledger:\n{render_ledger(state['claims_ledger'])}\n\n"
        f"Round {state['round_number']} persona turns:\n"
        f"{_render_round_turns(state['transcript'], state['round_number'])}"
    )
    extraction: RoundExtraction = await llm.ainvoke(
        [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    writer = get_stream_writer()
    ledger = list(state["claims_ledger"])
    ledger_by_id = {c["id"]: c for c in ledger}
    next_id_num = len(ledger) + 1
    new_claims_count = 0
    resolved_count = 0

    for item in extraction.classifications:
        if item.action == "new":
            claim: Claim = {
                "id": f"c{next_id_num}",
                "text": item.text,
                "raised_by": item.raised_by,
                "round_introduced": state["round_number"],
                "stance": normalize_stance(item.stance, state["options"]),
                "contested": True,
                "reinforced_count": 0,
                "resolved_round": None,
                "resolved_by": None,
            }
            ledger.append(claim)
            ledger_by_id[claim["id"]] = claim
            next_id_num += 1
            new_claims_count += 1
            writer({"type": "claim_added", "claim": dict(claim)})
        elif item.action == "restatement" and item.target_claim_id in ledger_by_id:
            ledger_by_id[item.target_claim_id]["reinforced_count"] += 1
        elif item.action == "resolution" and item.target_claim_id in ledger_by_id:
            target = ledger_by_id[item.target_claim_id]
            if target["contested"]:
                target["contested"] = False
                target["resolved_round"] = state["round_number"]
                target["resolved_by"] = item.raised_by
                resolved_count += 1
                writer(
                    {
                        "type": "claim_resolved",
                        "claim_id": target["id"],
                        "resolved_by": item.raised_by,
                        "round": state["round_number"],
                    }
                )

    return {
        "claims_ledger": ledger,
        "new_claims_this_round": new_claims_count,
        "resolved_this_round": resolved_count,
    }
