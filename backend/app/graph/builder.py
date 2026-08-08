"""Assembles the LangGraph StateGraph.

Milestone 1 scope: intake -> gather_evidence -> single debate turn -> end.
Convergence looping, claim extraction, synthesis, and human review are added
in later milestones as the full graph described in the PRD comes online.
"""

from langgraph.graph import END, StateGraph

from app.graph.nodes.debate import single_persona_round_node
from app.graph.nodes.evidence import gather_evidence_node
from app.graph.nodes.intake import intake_node
from app.graph.state import DecisionState


def build_graph():
    """Compile the (currently partial) debate StateGraph."""
    graph = StateGraph(DecisionState)

    graph.add_node("intake", intake_node)
    graph.add_node("gather_evidence", gather_evidence_node)
    graph.add_node("debate_round", single_persona_round_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "gather_evidence")
    graph.add_edge("gather_evidence", "debate_round")
    graph.add_edge("debate_round", END)

    return graph.compile()
