"""Custom MCP server exposing web search as a tool for the evidence node.

Wraps Serper (Google search results API) behind the MCP protocol (via the
official Python SDK) rather than calling the search API directly, so evidence
gathering is reachable through the same MCP client machinery as any other
tool server.
"""

import requests
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("evidence-server")

SERPER_ENDPOINT = "https://google.serper.dev/search"


@mcp.tool()
def search_web(query: str, max_results: int = 4) -> list[dict]:
    """Search the web and return title/snippet/url results for a query.

    Args:
        query: the search query, grounded in the decision's specifics.
        max_results: how many results to return (2-4 typical per PRD).
    """
    response = requests.post(
        SERPER_ENDPOINT,
        headers={
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json",
        },
        json={"q": query, "num": max_results},
        timeout=15,
    )
    response.raise_for_status()
    organic_results = response.json().get("organic", [])
    return [
        {
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "url": result.get("link", ""),
        }
        for result in organic_results[:max_results]
    ]


if __name__ == "__main__":
    mcp.run()
