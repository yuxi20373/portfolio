"""Web-search tool exposed to the deep agent. Uses Tavily if
TAVILY_API_KEY is configured (better quality), otherwise falls back to
DuckDuckGo search, which needs no API key at all.
"""

from langchain_core.tools import tool

from ...config import settings


@tool
def web_search(query: str) -> str:
    """Search the web for current information and return the top results
    (title, url, and a short snippet) as plain text. Use this whenever the
    answer depends on something recent, fast-changing, or that you're not
    confident you already know."""
    if settings.tavily_api_key:
        return _search_tavily(query)
    return _search_duckduckgo(query)


def _search_tavily(query: str) -> str:
    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(query, max_results=5)
    lines = [
        f"- {r.get('title', '')}: {r.get('url', '')}\n  {r.get('content', '')[:200]}"
        for r in response.get("results", [])
    ]
    return "\n".join(lines) or "No results found."


def _search_duckduckgo(query: str) -> str:
    from ddgs import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))
    lines = [f"- {r.get('title', '')}: {r.get('href', '')}\n  {r.get('body', '')[:200]}" for r in results]
    return "\n".join(lines) or "No results found."
