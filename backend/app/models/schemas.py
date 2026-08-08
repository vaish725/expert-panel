"""Pydantic schemas for structured LLM outputs.

Only the persona nodes produce free text; every other node (intake parsing,
claim classification, synthesis) constrains its LLM call to one of these
schemas via structured output, so downstream code never has to parse prose.
"""

from pydantic import BaseModel, Field


class IntakeExtraction(BaseModel):
    """Output of the intake node's structured-output LLM call.

    Cleans up the user's raw submission and surfaces stakes/constraints the
    user implied but never stated outright, so they can be confirmed rather
    than silently assumed before the debate starts.
    """

    decision_question: str = Field(description="The decision, restated clearly and neutrally.")
    options: list[str] = Field(description="The distinct options being weighed, at least two.")
    implicit_stakes: list[str] = Field(
        default_factory=list,
        description="Stakes the user implied but did not state explicitly, for user confirmation.",
    )
    implicit_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints the user implied but did not state explicitly, for user confirmation.",
    )


class EvidenceQueries(BaseModel):
    """Output of the evidence node's query-generation call: 2-4 search
    queries grounded in the decision's specifics, issued once before round 1."""

    queries: list[str] = Field(description="2 to 4 targeted web search queries.")
