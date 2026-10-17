"""Web fetch tool: read the relevant parts of specific pages found via search.

Backed by Tavily `extract`, so pages are fetched and cleaned by Tavily, never by
this process: URLs chosen by an agent cannot reach our network.
"""

import logging
from typing import Any
from urllib.parse import urlparse

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from dont_be_a_dick.tools.tavily_calls import TavilyCallError, call_with_retries

logger = logging.getLogger(__name__)

MAX_URLS = 3
MAX_CONTENT_CHARS = 8000
CHUNKS_PER_SOURCE = 3
REQUEST_TIMEOUT_SECONDS = 30.0


class FetchedPage(BaseModel):
    url: str
    content: str = Field(description="Relevant text from the page, possibly truncated")
    truncated: bool = False


class WebFetchToolOutput(BaseModel):
    pages: list[FetchedPage] = Field(default_factory=list)
    failed_urls: list[str] = Field(default_factory=list)
    error: str | None = None


def _error(message: str, failed_urls: list[str] | None = None) -> dict:
    logger.error(message)
    return WebFetchToolOutput(error=message, failed_urls=failed_urls or []).model_dump()


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def fetch_pages(client: Any, urls: list[str], query: str) -> dict:
    """Extract the parts of `urls` relevant to `query`, as a `WebFetchToolOutput` dict.

    Never raises: failures are reported through `error` and `failed_urls`.
    """
    query = query.strip()
    if not query:
        return _error("Invalid query: cannot be empty")

    unique = list(dict.fromkeys(u.strip() for u in urls if u.strip()))
    if not unique:
        return _error("No URLs given")
    if len(unique) > MAX_URLS:
        return _error(f"Too many URLs ({len(unique)}); fetch at most {MAX_URLS} at a time")

    valid = [u for u in unique if _is_http_url(u)]
    rejected = [u for u in unique if u not in valid]
    if not valid:
        return _error("Only http(s) URLs can be fetched", failed_urls=rejected)

    try:
        response = call_with_retries(
            lambda: client.extract(
                urls=valid,
                query=query,
                chunks_per_source=CHUNKS_PER_SOURCE,
                extract_depth="basic",
                format="text",
                timeout=REQUEST_TIMEOUT_SECONDS,
            ),
            what="extract",
        )
    except TavilyCallError as e:
        return _error(str(e), failed_urls=unique)

    pages = []
    for result in response.get("results") or []:
        content = result.get("raw_content") or ""
        pages.append(
            FetchedPage(
                url=result["url"],
                content=content[:MAX_CONTENT_CHARS],
                truncated=len(content) > MAX_CONTENT_CHARS,
            )
        )
    failed = rejected + [f["url"] for f in response.get("failed_results") or []]
    error = None if pages else "Could not fetch any of the given URLs"
    if error:
        logger.error(error)
    return WebFetchToolOutput(pages=pages, failed_urls=failed, error=error).model_dump()


def make_web_fetch_tool(client: Any) -> BaseTool:
    """Build the `web_fetch` tool bound to the given Tavily client.

    Args:
        client: Anything with a Tavily-compatible `extract(urls=..., query=..., ...)` method.
    """

    @tool
    def web_fetch(urls: list[str], query: str) -> dict:
        """Read the parts of specific web pages that are relevant to a question.

        Use this after web_search when a result's snippet is not enough detail.

        Args:
            urls: One to three http(s) URLs, taken from search results.
            query: What you want to learn from the pages. Only relevant passages are returned.

        Returns:
            A dict with `pages` (url, content), `failed_urls`, and an `error` message
            that is set when nothing could be fetched.
        """
        return fetch_pages(client, urls, query)

    return web_fetch
