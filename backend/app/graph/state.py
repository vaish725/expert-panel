"""LangGraph state schema for a debate: the single source of truth the graph
reads from and writes to at every node."""

from typing import Optional, TypedDict


class PersonaConfig(TypedDict):
    """Identity of one debating persona; node_id tags its streamed events."""

    name: str  # "skeptic" | "optimist" | "contrarian" | "pragmatist"
    system_prompt: str
    node_id: str


class Claim(TypedDict):
    """One distinct argument raised during the debate, tracked with provenance."""

    id: str
    text: str
    raised_by: str
    round_introduced: int
    stance: str  # option name, or "neutral"
    contested: bool
    reinforced_count: int
    resolved_round: Optional[int]
    resolved_by: Optional[str]


class Turn(TypedDict):
    """One persona's free-text response within a single round."""

    round: int
    persona: str
    content: str


class StructuredRecommendation(TypedDict):
    """Final synthesis output presented at the human-review gate."""

    recommended_option: Optional[str]
    tradeoffs: dict[str, list[dict]]  # option -> [{claim_id, direction: "pro"|"con"}]
    unresolved_disagreements: list[str]  # claim ids
    confidence_note: str


class DecisionState(TypedDict):
    """Full state of one debate thread, persisted by the LangGraph checkpointer."""

    thread_id: str
    decision_question: str
    options: list[str]
    user_context: str
    evidence: list[dict]  # {source, snippet, url}
    personas: list[PersonaConfig]
    transcript: list[Turn]
    claims_ledger: list[Claim]
    round_number: int
    min_rounds: int
    max_rounds: int
    new_claims_this_round: int
    resolved_this_round: int
    converged: bool
    forced: bool
    final_recommendation: Optional[StructuredRecommendation]
    human_approved: bool
