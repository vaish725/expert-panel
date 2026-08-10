"""Convergence-check node and its routing function.

The decision logic itself lives in app.graph.convergence as a pure function;
this module only persists that decision into state (a node needs somewhere
to write) and exposes a routing function for the conditional edge, which
reads state but never mutates it.
"""

from langgraph.config import get_stream_writer

from app.graph.convergence import check_convergence
from app.graph.personas.prompts import PERSONAS
from app.graph.state import DecisionState

PERSONA_NODE_NAMES = [p["node_id"] for p in PERSONAS]


def check_convergence_node(state: DecisionState) -> dict:
    """Persist the convergence decision and advance the round counter when
    the debate continues to another round."""
    result = check_convergence(
        round_number=state["round_number"],
        new_claims_this_round=state["new_claims_this_round"],
        resolved_this_round=state["resolved_this_round"],
        min_rounds=state["min_rounds"],
        max_rounds=state["max_rounds"],
    )

    writer = get_stream_writer()
    writer(
        {
            "type": "round_complete",
            "round": state["round_number"],
            "new_claims": state["new_claims_this_round"],
            "resolved": state["resolved_this_round"],
            "converged": result.converged,
        }
    )
    if result.converged:
        writer({"type": "converged", "round": state["round_number"], "forced": result.forced})

    update = {"converged": result.converged, "forced": result.forced}
    if not result.converged:
        update["round_number"] = state["round_number"] + 1
    return update


def route_after_convergence(state: DecisionState) -> str | list[str]:
    """Conditional edge: loop back to all 4 persona nodes for another round,
    or proceed to synthesis. Pure read of already-computed state, no side effects."""
    if state["converged"]:
        return "synthesize"
    return PERSONA_NODE_NAMES
