import pytest
from tavily import TavilyClient
from tavily.errors import (
    BadRequestError,
    InvalidAPIKeyError,
    UsageLimitExceededError,
)
from tavily.errors import (
    TimeoutError as TavilyTimeoutError,
)

from dont_be_a_dick.config import Settings
from dont_be_a_dick.tools.tavily_calls import MAX_RETRIES
from dont_be_a_dick.tools.web_search import WebSearchToolOutput, make_web_search_tool

RAW_RESULT = {
    "url": "https://example.com/a",
    "title": "Example",
    "content": "Some content",
    "score": 0.9,
    "raw_content": None,
    "id": "abc",
}


class FakeTavilyClient:
    """Returns queued responses; raises any queued exception instances."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.queries: list[str] = []

    def search(self, query: str, **kwargs):
        self.queries.append(query)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def run(client: FakeTavilyClient, query: str = "someone") -> WebSearchToolOutput:
    tool = make_web_search_tool(client)
    return WebSearchToolOutput.model_validate(tool.invoke({"query": query}))


def test_tool_metadata() -> None:
    tool = make_web_search_tool(FakeTavilyClient())

    assert tool.name == "web_search"
    assert "search" in tool.description.lower()
    assert set(tool.args) == {"query"}


def test_returns_validated_results() -> None:
    output = run(FakeTavilyClient({"results": [RAW_RESULT]}))

    assert output.error is None
    assert [r.url for r in output.results] == ["https://example.com/a"]


def test_uses_the_injected_client() -> None:
    client = FakeTavilyClient({"results": [RAW_RESULT]})

    run(client, "  Peter Singer  ")

    assert client.queries == ["Peter Singer"]


@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query_is_rejected_without_calling_client(query: str) -> None:
    client = FakeTavilyClient()

    output = run(client, query)

    assert output.error is not None
    assert "empty" in output.error.lower()
    assert client.queries == []


def test_no_results() -> None:
    output = run(FakeTavilyClient({"results": []}))

    assert output.results == []
    assert output.error == "No results found"


def test_malformed_results_are_reported() -> None:
    output = run(FakeTavilyClient({"results": [{"url": "https://x.com"}]}))

    assert output.results == []
    assert output.error is not None
    assert "validate" in output.error.lower()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (InvalidAPIKeyError("bad key"), "Authentication error"),
        (BadRequestError("bad param"), "Fatal parameter error"),
    ],
)
def test_non_retryable_errors_fail_immediately(error: Exception, expected: str) -> None:
    client = FakeTavilyClient(error)

    output = run(client)

    assert expected in (output.error or "")
    assert len(client.queries) == 1


@pytest.mark.parametrize("error", [UsageLimitExceededError("slow down"), TavilyTimeoutError(15.0)])
def test_retryable_errors_are_retried_then_succeed(error: Exception) -> None:
    client = FakeTavilyClient(error, {"results": [RAW_RESULT]})

    output = run(client)

    assert output.error is None
    assert len(client.queries) == 2


def test_retryable_errors_give_up_after_max_retries() -> None:
    client = FakeTavilyClient(*[UsageLimitExceededError("slow down")] * MAX_RETRIES)

    output = run(client)

    assert output.results == []
    assert f"{MAX_RETRIES} attempts" in (output.error or "")
    assert len(client.queries) == MAX_RETRIES


def test_unexpected_errors_are_reported_not_raised() -> None:
    output = run(FakeTavilyClient(RuntimeError("boom")))

    assert "RuntimeError" in (output.error or "")


@pytest.mark.integration
def test_real_tavily_search() -> None:
    settings = Settings()
    if not settings.tavily_api_key.get_secret_value():
        pytest.skip("DBAD_TAVILY_API_KEY not set")
    tool = make_web_search_tool(TavilyClient(api_key=settings.tavily_api_key.get_secret_value()))

    output = WebSearchToolOutput.model_validate(tool.invoke({"query": "Peter Singer"}))

    assert output.error is None
    assert len(output.results) > 0
