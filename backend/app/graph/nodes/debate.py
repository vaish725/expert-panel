"""Debate round nodes: all 4 personas respond in parallel each round.

Each persona is a separate LangGraph node so the scheduler runs them
concurrently (fan-out from gather_evidence / check_convergence, fan-in to
extract_claims) rather than sequentially. No persona sees another's
current-round response until the round completes, per the PRD.
"""

from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.graph.personas.prompts import get_persona, render_round_prompt
from app.graph.state import DecisionState, Turn


def _build_persona_llm() -> ChatAnthropic:
    # no explicit temperature: this model rejects the parameter outright
    # and uses its own fixed default for all calls
    return ChatAnthropic(
        model=settings.persona_model,
        api_key=settings.anthropic_api_key,
    )


def _extract_text(content) -> str:
    """This model reasons by default, so response.content is a list of
    blocks (thinking + text) rather than a plain string; keep only the text."""
    if isinstance(content, str):
        return content
    text_blocks = [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"]
    return "\n".join(text_blocks).strip()


async def _run_persona_turn(state: DecisionState, persona_name: str) -> dict:
    """Shared logic behind each persona node: render its prompt, call the
    model, and append its turn to the transcript."""
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
        "content": _extract_text(response.content),
    }
    return {"transcript": [turn]}


# one thin node per persona, so LangGraph can schedule all 4 concurrently;
# node names match each persona's node_id (app/graph/personas/prompts.py)
# so streamed events can later be tagged consistently.
async def persona_skeptic(state: DecisionState) -> dict:
    return await _run_persona_turn(state, "skeptic")


async def persona_optimist(state: DecisionState) -> dict:
    return await _run_persona_turn(state, "optimist")


async def persona_contrarian(state: DecisionState) -> dict:
    return await _run_persona_turn(state, "contrarian")


async def persona_pragmatist(state: DecisionState) -> dict:
    return await _run_persona_turn(state, "pragmatist")
