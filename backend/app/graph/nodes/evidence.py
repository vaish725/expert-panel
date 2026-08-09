"""Evidence node: runs once before round 1, grounding the debate in real
search results fetched through the evidence-server MCP tool.

Evidence is not re-fetched mid-debate in v1 (cost/latency control); personas
work from this snapshot plus any user-uploaded documents.
"""

import json
import sys
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import settings
from app.graph.state import DecisionState
from app.models.schemas import EvidenceQueries

QUERY_SYSTEM_PROMPT = """Generate 2 to 4 targeted web search queries that would surface \
useful, current evidence for the decision below. Queries should be specific to the \
decision's details, not generic advice searches."""

# backend project root, needed so the subprocess can resolve `app.*` imports
# when launched as a module rather than a bare script path
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _build_query_llm() -> ChatAnthropic:
    # no explicit temperature: this model rejects the parameter outright
    return ChatAnthropic(
        model=settings.structured_model,
        api_key=settings.anthropic_api_key,
    ).with_structured_output(EvidenceQueries)


async def gather_evidence_node(state: DecisionState) -> dict:
    """Generate grounded search queries, run them through the MCP evidence
    server, and store the results in the shared evidence pool."""
    llm = _build_query_llm()
    prompt = (
        f"Decision: {state['decision_question']}\n"
        f"Options: {', '.join(state['options'])}\n"
        f"Context: {state.get('user_context') or '(none provided)'}"
    )
    query_plan: EvidenceQueries = await llm.ainvoke(
        [
            {"role": "system", "content": QUERY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
    )

    client = MultiServerMCPClient(
        {
            "evidence": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "app.mcp_servers.evidence_server.server"],
                "cwd": str(_BACKEND_ROOT),
            }
        }
    )
    tools = await client.get_tools()
    search_web = next(tool for tool in tools if tool.name == "search_web")

    evidence: list[dict] = []
    for query in query_plan.queries[:4]:
        # each list item is an MCP text content block whose "text" field is
        # a JSON-serialized {title, snippet, url} dict, not the dict itself
        content_blocks = await search_web.ainvoke({"query": query, "max_results": 3})
        for block in content_blocks:
            result = json.loads(block["text"])
            evidence.append(
                {
                    "source": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("url", ""),
                }
            )

    return {"evidence": evidence}
