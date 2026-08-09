"""Assembles the LangGraph StateGraph.

Milestone 2 scope: intake -> gather_evidence -> 4 parallel personas ->
extract_claims -> check_convergence, looping back to the personas until
convergence. Synthesis, human review, and export are added in milestone 3.
"""

from langgraph.graph import StateGraph

from app.graph.nodes.convergence import PERSONA_NODE_NAMES, check_convergence_node, route_after_convergence
from app.graph.nodes.debate import persona_contrarian, persona_optimist, persona_pragmatist, persona_skeptic
from app.graph.nodes.evidence import gather_evidence_node
from app.graph.nodes.extraction import extract_claims_node
from app.graph.nodes.intake import intake_node
from app.graph.state import DecisionState

_PERSONA_NODE_FUNCS = {
    "persona_skeptic": persona_skeptic,
    "persona_optimist": persona_optimist,
    "persona_contrarian": persona_contrarian,
    "persona_pragmatist": persona_pragmatist,
}


def build_graph():
    """Compile the debate StateGraph."""
    graph = StateGraph(DecisionState)

    graph.add_node("intake", intake_node)
    graph.add_node("gather_evidence", gather_evidence_node)
    for node_name in PERSONA_NODE_NAMES:
        graph.add_node(node_name, _PERSONA_NODE_FUNCS[node_name])
    graph.add_node("extract_claims", extract_claims_node)
    graph.add_node("check_convergence", check_convergence_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "gather_evidence")

    # fan-out: all 4 personas run in parallel off evidence gathering
    for node_name in PERSONA_NODE_NAMES:
        graph.add_edge("gather_evidence", node_name)
        # fan-in: extraction waits for all 4 to finish
        graph.add_edge(node_name, "extract_claims")

    graph.add_edge("extract_claims", "check_convergence")
    # loop back to all 4 personas for another round, or stop
    graph.add_conditional_edges("check_convergence", route_after_convergence)

    return graph.compile()
