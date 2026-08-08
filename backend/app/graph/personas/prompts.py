"""Persona definitions: fixed set of 4, not user-configurable in v1.

Each persona has a distinct epistemic function, not just a personality, and a
prompted constraint that keeps its output machine-parseable downstream (the
Contrarian's claim-ID references, the Pragmatist's ungrounded-claim flags).
"""

from app.graph.state import DecisionState, PersonaConfig

PERSONAS: list[PersonaConfig] = [
    {
        "name": "skeptic",
        "node_id": "persona_skeptic",
        "system_prompt": (
            "You are the Skeptic in a structured decision debate. Your job is to surface "
            "downside scenarios, base rates of failure, and sunk-cost traps that others miss. "
            "You must name a concrete failure scenario, not just express general doubt."
        ),
    },
    {
        "name": "optimist",
        "node_id": "persona_optimist",
        "system_prompt": (
            "You are the Optimist in a structured decision debate. Your job is to surface "
            "upside, option value, and the cost of inaction. You must quantify or bound the "
            "upside where possible, not just assert it exists."
        ),
    },
    {
        "name": "contrarian",
        "node_id": "persona_contrarian",
        "system_prompt": (
            "You are the Contrarian in a structured decision debate. Your job is to attack "
            "whichever argument currently has the most support in the claims ledger, and to "
            "steelman the least-favored option. You must explicitly reference the claim ID "
            "you are attacking, e.g. 'Regarding c3: ...'."
        ),
    },
    {
        "name": "pragmatist",
        "node_id": "persona_pragmatist",
        "system_prompt": (
            "You are the Pragmatist in a structured decision debate. Your job is evidentiary "
            "discipline: you may only assert claims traceable to retrieved evidence or "
            "user-supplied documents, and you must flag ungrounded claims from other personas "
            "by their claim ID."
        ),
    },
]


def get_persona(name: str) -> PersonaConfig:
    """Look up a persona config by name."""
    for persona in PERSONAS:
        if persona["name"] == name:
            return persona
    raise ValueError(f"unknown persona: {name}")


def render_round_prompt(state: DecisionState, persona: PersonaConfig) -> str:
    """Build the user-turn prompt a persona sees for the current round: the
    decision, evidence, transcript so far, and the live claims ledger."""
    evidence_block = "\n".join(
        f"- {e['source']}: {e['snippet']} ({e['url']})" for e in state.get("evidence", [])
    ) or "(no evidence gathered yet)"

    transcript_block = "\n".join(
        f"[round {t['round']}] {t['persona']}: {t['content']}" for t in state.get("transcript", [])
    ) or "(no prior turns)"

    ledger_block = "\n".join(
        f"- {c['id']} ({c['stance']}, {'contested' if c['contested'] else 'resolved'}): {c['text']}"
        for c in state.get("claims_ledger", [])
    ) or "(no claims raised yet)"

    return (
        f"Decision: {state['decision_question']}\n"
        f"Options: {', '.join(state['options'])}\n"
        f"Context: {state.get('user_context') or '(none)'}\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        f"Transcript so far:\n{transcript_block}\n\n"
        f"Claims ledger:\n{ledger_block}\n\n"
        f"Round {state['round_number']}: give your response as {persona['name']}."
    )
