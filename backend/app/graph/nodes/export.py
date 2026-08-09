"""Export node: the graph pauses immediately before this node (interrupt_before
in the compiled graph); it only runs once a human has explicitly approved the
recommendation, per PRD 5.7. Calls the document-generator MCP server to
render the final Markdown report with the full claims-ledger audit trail.
"""

import json
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.graph.state import DecisionState

# backend project root, needed so the subprocess can resolve `app.*` imports
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


async def export_node(state: DecisionState) -> dict:
    """Generate and write the final report; assumes approval already happened
    (the interrupt_before gate is what actually enforces that in the graph)."""
    if not state.get("human_approved"):
        raise RuntimeError("export_node reached without human approval")

    client = MultiServerMCPClient(
        {
            "document_generator": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "app.mcp_servers.document_generator_server.server"],
                "cwd": str(_BACKEND_ROOT),
            }
        }
    )
    tools = await client.get_tools()
    generate_report = next(tool for tool in tools if tool.name == "generate_report")

    # single-item MCP text content block whose "text" is the JSON-serialized
    # {path, format} result, not the dict itself
    content_blocks = await generate_report.ainvoke({"decision": dict(state)})
    result = json.loads(content_blocks[0]["text"])

    return {"exported_report_path": result["path"]}
