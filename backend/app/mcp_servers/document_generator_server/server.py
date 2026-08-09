"""Custom MCP server that renders a finished debate as a Markdown report,
including the full claims ledger as an audit-trail appendix.

Used once per debate, by the export node, after human approval.
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("document-generator-server")

# project-root reports/ directory (backend/../reports), not inside backend/
_REPORTS_DIR = Path(__file__).resolve().parents[4] / "reports"


def _render_report(decision: dict) -> str:
    recommendation = decision.get("final_recommendation") or {}
    lines = [
        f"# Decision Report: {decision.get('decision_question', '')}",
        "",
        f"**Options considered:** {', '.join(decision.get('options', []))}",
        "",
        "## Recommendation",
        "",
        f"**Recommended option:** {recommendation.get('recommended_option') or 'No clear recommendation (see confidence note)'}",
        "",
        f"**Confidence note:** {recommendation.get('confidence_note', '')}",
        "",
        "## Tradeoffs",
        "",
    ]

    for option, items in (recommendation.get("tradeoffs") or {}).items():
        lines.append(f"### {option}")
        for item in items:
            lines.append(f"- ({item['direction']}) {item['claim_id']}")
        lines.append("")

    unresolved = recommendation.get("unresolved_disagreements") or []
    if unresolved:
        lines.append("## Unresolved disagreements")
        lines.append("")
        lines.extend(f"- {claim_id}" for claim_id in unresolved)
        lines.append("")

    lines.append("## Claims ledger (audit trail)")
    lines.append("")
    for claim in decision.get("claims_ledger", []):
        status = "contested" if claim["contested"] else f"resolved (round {claim['resolved_round']})"
        lines.append(
            f"- **{claim['id']}** [{claim['stance']}, {status}, reinforced x{claim['reinforced_count']}] "
            f"(raised by {claim['raised_by']}, round {claim['round_introduced']}): {claim['text']}"
        )

    return "\n".join(lines)


@mcp.tool()
def generate_report(decision: dict) -> dict:
    """Render the final debate as a Markdown report and write it to disk.

    Args:
        decision: the full debate state (decision question, options, final
            recommendation, claims ledger, thread_id).
    """
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    thread_id = decision.get("thread_id", "debate")
    path = _REPORTS_DIR / f"{thread_id}.md"
    path.write_text(_render_report(decision), encoding="utf-8")
    return {"path": str(path), "format": "markdown"}


if __name__ == "__main__":
    mcp.run()
