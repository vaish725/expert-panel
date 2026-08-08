"""Custom MCP server exposing web search as a tool for the evidence node.

Wraps Tavily behind the MCP protocol (via the official Python SDK) rather
than calling the search API directly, so evidence gathering is reachable
through the same MCP client machinery as any other tool server.
"""

from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

from app.config import settings

mcp = FastMCP("evidence-server")


@mcp.tool()
def search_web(query: str, max_results: int = 4) -> list[dict]:
    """Search the web and return title/snippet/url results for a query.

    Args:
        query: the search query, grounded in the decision's specifics.
        max_results: how many results to return (2-4 typical per PRD).
    """
    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(query=query, max_results=max_results)
    return [
        {
            "title": result.get("title", ""),
            "snippet": result.get("content", ""),
            "url": result.get("url", ""),
        }
        for result in response.get("results", [])
    ]


if __name__ == "__main__":
    mcp.run()
