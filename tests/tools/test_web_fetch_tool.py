from typing import Any

import pytest
from tavily import TavilyClient
from tavily.errors import InvalidAPIKeyError, UsageLimitExceededError

from dont_be_a_dick.config import Settings
from dont_be_a_dick.tools.tavily_calls import MAX_RETRIES
from dont_be_a_dick.tools.web_fetch import (
    MAX_CONTENT_CHARS,
    MAX_URLS,
    WebFetchToolOutput,
    make_web_fetch_tool,
)

PAGE = {"url": "https://example.com/a", "raw_content": "Relevant text."}


class FakeTavilyClient:
    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def extract(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def run(
    client: FakeTavilyClient, urls: list[str], query: str = "safety team"
) -> WebFetchToolOutput:
    tool = make_web_fetch_tool(client)
    return WebFetchToolOutput.model_validate(tool.invoke({"urls": urls, "query": query}))


def test_tool_metadata() -> None:
    tool = make_web_fetch_tool(FakeTavilyClient())

    assert tool.name == "web_fetch"
    assert set(tool.args) == {"urls", "query"}


def test_returns_pages_and_passes_the_query_to_tavily() -> None:
    client = FakeTavilyClient({"results": [PAGE], "failed_results": []})

    output = run(client, ["https://example.com/a"], query="  safety team ")

    assert output.error is None
    assert [p.url for p in output.pages] == ["https://example.com/a"]
    assert output.pages[0].content == "Relevant text."
    [call] = client.calls
    assert call["urls"] == ["https://example.com/a"]
    assert call["query"] == "safety team"


def test_long_content_is_truncated() -> None:
    long_page = {"url": "https://example.com/a", "raw_content": "x" * (MAX_CONTENT_CHARS + 50)}

    output = run(FakeTavilyClient({"results": [long_page]}), ["https://example.com/a"])

    assert len(output.pages[0].content) == MAX_CONTENT_CHARS
    assert output.pages[0].truncated is True


def test_non_http_urls_are_rejected_without_calling_tavily() -> None:
    client = FakeTavilyClient()

    output = run(client, ["file:///etc/passwd", "ftp://example.com/x"])

    assert output.error == "Only http(s) URLs can be fetched"
    assert output.failed_urls == ["file:///etc/passwd", "ftp://example.com/x"]
    assert client.calls == []


def test_valid_urls_are_fetched_and_invalid_ones_reported() -> None:
    client = FakeTavilyClient({"results": [PAGE]})

    output = run(client, ["https://example.com/a", "javascript:alert(1)"])

    assert [p.url for p in output.pages] == ["https://example.com/a"]
    assert output.failed_urls == ["javascript:alert(1)"]
    assert output.error is None
    assert client.calls[0]["urls"] == ["https://example.com/a"]


def test_too_many_urls_is_rejected() -> None:
    client = FakeTavilyClient()
    urls = [f"https://example.com/{i}" for i in range(MAX_URLS + 1)]

    output = run(client, urls)

    assert "Too many URLs" in (output.error or "")
    assert client.calls == []


@pytest.mark.parametrize(("urls", "query"), [([], "q"), ([" "], "q"), (["https://a.com"], "  ")])
def test_empty_input_is_rejected(urls: list[str], query: str) -> None:
    client = FakeTavilyClient()

    output = run(client, urls, query)

    assert output.error
    assert client.calls == []


def test_duplicate_urls_are_fetched_once() -> None:
    client = FakeTavilyClient({"results": [PAGE]})

    run(client, ["https://example.com/a", "https://example.com/a"])

    assert client.calls[0]["urls"] == ["https://example.com/a"]


def test_failed_results_are_reported_alongside_pages() -> None:
    response = {
        "results": [PAGE],
        "failed_results": [{"url": "https://bad.example/x", "error": "timeout"}],
    }

    output = run(FakeTavilyClient(response), ["https://example.com/a", "https://bad.example/x"])

    assert len(output.pages) == 1
    assert output.failed_urls == ["https://bad.example/x"]
    assert output.error is None


def test_all_pages_failing_sets_an_error() -> None:
    response = {"results": [], "failed_results": [{"url": "https://bad.example/x", "error": "x"}]}

    output = run(FakeTavilyClient(response), ["https://bad.example/x"])

    assert output.pages == []
    assert output.error == "Could not fetch any of the given URLs"
    assert output.failed_urls == ["https://bad.example/x"]


def test_auth_errors_are_not_retried() -> None:
    client = FakeTavilyClient(InvalidAPIKeyError("bad key"))

    output = run(client, ["https://example.com/a"])

    assert "Authentication error" in (output.error or "")
    assert len(client.calls) == 1


def test_rate_limits_are_retried() -> None:
    client = FakeTavilyClient(UsageLimitExceededError("slow"), {"results": [PAGE]})

    output = run(client, ["https://example.com/a"])

    assert output.error is None
    assert len(client.calls) == 2


def test_gives_up_after_max_retries() -> None:
    client = FakeTavilyClient(*[UsageLimitExceededError("slow")] * MAX_RETRIES)

    output = run(client, ["https://example.com/a"])

    assert f"{MAX_RETRIES} attempts" in (output.error or "")
    assert output.failed_urls == ["https://example.com/a"]


@pytest.mark.integration
def test_real_tavily_extract() -> None:
    settings = Settings()
    if not settings.tavily_api_key.get_secret_value():
        pytest.skip("DBAD_TAVILY_API_KEY not set")
    tool = make_web_fetch_tool(TavilyClient(api_key=settings.tavily_api_key.get_secret_value()))

    output = WebFetchToolOutput.model_validate(
        tool.invoke({"urls": ["https://en.wikipedia.org/wiki/Peter_Singer"], "query": "Princeton"})
    )

    assert output.error is None
    assert output.pages
    assert "princeton" in output.pages[0].content.lower()
