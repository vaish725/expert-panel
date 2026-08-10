"""Debate round nodes: all 4 personas respond in parallel each round.

Each persona is a separate LangGraph node so the scheduler runs them
concurrently (fan-out from gather_evidence / check_convergence, fan-in to
extract_claims) rather than sequentially. No persona sees another's
current-round response until the round completes, per the PRD.
"""

from langchain_anthropic import ChatAnthropic
from langgraph.config import get_stream_writer

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


def _text_delta(chunk_content) -> str:
    """This model reasons by default, so each streamed chunk's content is a
    list of partial blocks (thinking + text); keep only the text piece."""
    if isinstance(chunk_content, str):
        return chunk_content
    if not isinstance(chunk_content, list):
        return ""
    return "".join(
        block.get("text", "") for block in chunk_content if isinstance(block, dict) and block.get("type") == "text"
    )


async def _run_persona_turn(state: DecisionState, persona_name: str) -> dict:
    """Shared logic behind each persona node: stream its response token by
    token (emitting a custom "token" event per delta for the WS layer to
    relay live), then append the assembled turn to the transcript."""
    persona = get_persona(persona_name)
    llm = _build_persona_llm()
    prompt = render_round_prompt(state, persona)
    writer = get_stream_writer()

    full_text_parts: list[str] = []
    async for chunk in llm.astream(
        [
            {"role": "system", "content": persona["system_prompt"]},
            {"role": "user", "content": prompt},
        ]
    ):
        delta = _text_delta(chunk.content)
        if delta:
            full_text_parts.append(delta)
            writer(
                {
                    "type": "token",
                    "node": persona["node_id"],
                    "round": state["round_number"],
                    "delta": delta,
                }
            )

    turn: Turn = {
        "round": state["round_number"],
        "persona": persona["name"],
        "content": "".join(full_text_parts).strip(),
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
