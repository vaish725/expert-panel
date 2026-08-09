"""Debate round node.

Milestone 1 scope: a single persona (the Skeptic) responds once, to prove the
intake -> evidence -> debate pipeline end-to-end. Fanning this out to all 4
personas running in parallel per round is the next milestone.
"""

from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.graph.personas.prompts import get_persona, render_round_prompt
from app.graph.state import DecisionState, Turn


def _build_persona_llm() -> ChatAnthropic:
    """Higher temperature: distinct persona voices matter more than
    determinism here, unlike the structured-output nodes."""
    return ChatAnthropic(
        model=settings.persona_model,
        temperature=0.7,
        api_key=settings.anthropic_api_key,
    )


async def single_persona_round_node(state: DecisionState, persona_name: str = "skeptic") -> dict:
    """Run one persona for the current round and append its turn to the transcript."""
    persona = get_persona(persona_name)
    llm = _build_persona_llm()
    prompt = render_round_prompt(state, persona)

    response = await llm.ainvoke(
        [
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "user", "content": prompt},
        ]
    )

    turn: Turn = {
        "round": state["round_number"],
        "persona": persona["name"],
        "content": response.content,
    }
    return {"transcript": state["transcript"] + [turn]}
