"""Assembles the LangGraph StateGraph.

Full v1 loop: intake -> gather_evidence -> 4 parallel personas ->
extract_claims -> check_convergence, looping back to the personas until
convergence, then synthesize -> [pause for human review] -> export.
"""

from langgraph.graph import StateGraph

from app.graph.nodes.convergence import PERSONA_NODE_NAMES, check_convergence_node, route_after_convergence
from app.graph.nodes.debate import persona_contrarian, persona_optimist, persona_pragmatist, persona_skeptic
from app.graph.nodes.evidence import gather_evidence_node
from app.graph.nodes.export import export_node
from app.graph.nodes.extraction import extract_claims_node
from app.graph.nodes.intake import intake_node
from app.graph.nodes.synthesis import synthesize_node
from app.graph.state import DecisionState

_PERSONA_NODE_FUNCS = {
    "persona_skeptic": persona_skeptic,
    "persona_optimist": persona_optimist,
    "persona_contrarian": persona_contrarian,
    "persona_pragmatist": persona_pragmatist,
}


def build_graph(checkpointer=None):
    """Compile the debate StateGraph.

    A checkpointer is required for the human-review pause to be a real pause
    (survives process restarts/browser disconnects) rather than an in-memory
    block; pass None only for structural checks that never cross the interrupt.
    """
    graph = StateGraph(DecisionState)

    graph.add_node("intake", intake_node)
    graph.add_node("gather_evidence", gather_evidence_node)
    for node_name in PERSONA_NODE_NAMES:
        graph.add_node(node_name, _PERSONA_NODE_FUNCS[node_name])
    graph.add_node("extract_claims", extract_claims_node)
    graph.add_node("check_convergence", check_convergence_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("export", export_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "gather_evidence")

    # fan-out: all 4 personas run in parallel off evidence gathering
    for node_name in PERSONA_NODE_NAMES:
        graph.add_edge("gather_evidence", node_name)
        # fan-in: extraction waits for all 4 to finish
        graph.add_edge(node_name, "extract_claims")

    graph.add_edge("extract_claims", "check_convergence")
    # loop back to all 4 personas for another round, or proceed to synthesis
    graph.add_conditional_edges("check_convergence", route_after_convergence)

    graph.add_edge("synthesize", "export")

    # pauses here until a human approves; export only runs after human_approved
    return graph.compile(checkpointer=checkpointer, interrupt_before=["export"])
