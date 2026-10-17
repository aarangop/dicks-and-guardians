"""Web search tool.

The Tavily client is injected through `make_web_search_tool`, which returns a
LangChain tool that closes over it. Nothing in this module reads settings or
environment variables.
"""

import logging
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field, ValidationError

from dont_be_a_dick.tools.tavily_calls import TavilyCallError, call_with_retries

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 1000
REQUEST_TIMEOUT_SECONDS = 15.0


class WebSearchResult(BaseModel):
    url: str = Field(..., description="URL of the search result")
    title: str = Field(..., description="Title of the search result")
    content: str = Field(..., description="Content or snippet of the search result")
    score: float = Field(..., description="Relevance score of the search result")
    raw_content: str | None = Field(default=None, description="Raw content of the search result")
    id: str | None = Field(default=None, description="Unique identifier of the search result")


class WebSearchToolOutput(BaseModel):
    results: list[WebSearchResult] = Field(..., description="List of web search results")
    error: str | None = Field(default=None, description="Error message if search failed")


def _error(message: str) -> dict:
    logger.error(message)
    return WebSearchToolOutput(results=[], error=message).model_dump()


def _normalize_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise ValueError("Query cannot be empty")
    if len(normalized) > MAX_QUERY_LENGTH:
        logger.warning(f"Query is very long ({len(normalized)} chars), truncating")
        normalized = normalized[:MAX_QUERY_LENGTH]
    return normalized


def search_web(client: Any, query: str) -> dict:
    """Run a Tavily search and return a `WebSearchToolOutput` as a dict.

    Never raises: failures are reported through the `error` field so the agent
    can see them and decide what to do.
    """
    try:
        query = _normalize_query(query)
    except ValueError as e:
        return _error(f"Invalid query: {e}")

    try:
        response = call_with_retries(
            lambda: client.search(query, timeout=REQUEST_TIMEOUT_SECONDS), what="search"
        )
    except TavilyCallError as e:
        return _error(str(e))

    raw_results = response.get("results") or []
    if not raw_results:
        return _error("No results found")

    try:
        return WebSearchToolOutput(results=[WebSearchResult(**r) for r in raw_results]).model_dump()
    except ValidationError as e:
        return _error(f"Failed to validate search results: {e!s}")


def make_web_search_tool(client: Any) -> BaseTool:
    """Build the `web_search` tool bound to the given Tavily client.

    Args:
        client: Anything with a Tavily-compatible `search(query, timeout=...)`
            method. In production a `tavily.TavilyClient`; in tests, a fake.
    """

    @tool
    def web_search(query: str) -> dict:
        """Search the web for information about a person or topic.

        Args:
            query: What to search for, e.g. a person's name plus a topic.

        Returns:
            A dict with `results` (url, title, content, score) and an `error`
            message that is set when the search failed.
        """
        return search_web(client, query)

    return web_search
