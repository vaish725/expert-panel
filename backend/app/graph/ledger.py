"""Shared claims-ledger rendering, used anywhere a prompt needs to show the
live ledger to an LLM (persona turns, extraction, synthesis)."""

from app.graph.state import Claim


def render_ledger(claims: list[Claim]) -> str:
    if not claims:
        return "(no claims raised yet)"
    return "\n".join(
        f"- {c['id']} [{c['stance']}, {'contested' if c['contested'] else 'resolved'}]: {c['text']}"
        for c in claims
    )
