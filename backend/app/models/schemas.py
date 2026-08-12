"""Pydantic schemas for structured LLM outputs.

Only the persona nodes produce free text; every other node (intake parsing,
claim classification, synthesis) constrains its LLM call to one of these
schemas via structured output, so downstream code never has to parse prose.
"""

from typing import Literal, Optional

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


class ClaimClassification(BaseModel):
    """One distinct assertion found in a round's persona turns, classified
    against the existing claims ledger. Paraphrases of an existing claim must
    be recognized as restatements/resolutions, not filed as new claims."""

    action: Literal["new", "restatement", "resolution"] = Field(
        description="Whether this assertion is a new claim, a restatement of an "
        "existing one, or a resolution (settles/concedes) of an existing one."
    )
    raised_by: str = Field(description="Persona who made this assertion this round.")
    text: str = Field(description="The claim text, for 'new' actions. Ignored otherwise.")
    stance: str = Field(
        default="neutral", description="Which option this claim favors, or 'neutral'. Only used for 'new'."
    )
    target_claim_id: Optional[str] = Field(
        default=None,
        description="For 'restatement' or 'resolution': the existing ledger claim id this refers to.",
    )


class RoundExtraction(BaseModel):
    """Output of the extract_claims node: every distinct assertion raised
    this round, across all 4 persona turns, classified in one structured call."""

    classifications: list[ClaimClassification]


class SynthesisOutput(BaseModel):
    """Output of the synthesize node's structured-output LLM call.

    Deliberately minimal. Two fields that were tried here and pulled back out:

    - tradeoffs: a claim's `stance` already says which option it favors, so
      the pro/con table is derived directly from the ledger in code (every
      claim is a "pro" for the option it favors and a "con" for the others).
      Asking the model to reproduce this as structured output was both
      redundant and unreliable in practice: on a schema this size, tool-call
      output twice came back malformed (once nested under a spurious
      wrapper key, once double-encoded as a JSON string) and retried
      identically each time, so it wasn't sampling noise, it was the model
      of the moment consistently struggling with this exact shape.
    - unresolved_disagreements: derived from the ledger's contested claims
      in code, not left to the model to recall correctly.
    """

    recommended_option: Optional[str] = Field(
        default=None,
        description="One of the decision's options, or null if the ledger is genuinely balanced.",
    )
    confidence_note: str = Field(
        description="Plain-language statement of how settled vs. contested the ledger is, citing claim ids. "
        "If recommended_option is null, explain why the ledger is genuinely balanced here."
    )
