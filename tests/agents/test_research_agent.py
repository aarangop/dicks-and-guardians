from collections.abc import Iterator
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.agents import build_research_agent
from dont_be_a_dick.config import Settings
from dont_be_a_dick.tools.web_search import WebSearchToolOutput, make_web_search_tool


class FakeToolCallingModel(GenericFakeChatModel):
    """Fake chat model that replays scripted messages and accepts bind_tools."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCallingModel":
        return self


def scripted(*messages: AIMessage) -> FakeToolCallingModel:
    iterator: Iterator[AIMessage] = iter(messages)
    return FakeToolCallingModel(messages=iterator)


def ask(agent, text: str) -> dict:
    return agent.invoke({"messages": [{"role": "user", "content": text}]})


def test_agent_answers_without_tools_when_model_does_not_call_them() -> None:
    @tool
    def web_search(query: str) -> str:
        """Search."""
        raise AssertionError("should not be called")

    agent = build_research_agent(
        model=scripted(AIMessage(content="Nothing to look up.")), tools=[web_search]
    )

    result = ask(agent, "Who is Peter Singer?")

    assert result["messages"][-1].content == "Nothing to look up."


def test_agent_calls_injected_tool_and_uses_its_result() -> None:
    calls: list[str] = []

    @tool
    def web_search(query: str) -> str:
        """Search the web."""
        calls.append(query)
        return "Peter Singer is a philosopher."

    model = scripted(
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search", "args": {"query": "Peter Singer"}, "id": "1"}],
        ),
        AIMessage(content="He is a philosopher."),
    )
    agent = build_research_agent(model=model, tools=[web_search])

    result = ask(agent, "Who is Peter Singer?")

    assert calls == ["Peter Singer"]
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_messages[0].content == "Peter Singer is a philosopher."
    assert result["messages"][-1].content == "He is a philosopher."


def test_agent_with_real_web_search_tool_and_fake_tavily_client() -> None:
    class FakeClient:
        def search(self, query: str, **kwargs: Any) -> dict:
            return {
                "results": [{"url": "https://x.com", "title": "T", "content": "C", "score": 0.5}]
            }

    model = scripted(
        AIMessage(
            content="",
            tool_calls=[{"name": "web_search", "args": {"query": "x"}, "id": "1"}],
        ),
        AIMessage(content="done"),
    )
    agent = build_research_agent(model=model, tools=[make_web_search_tool(FakeClient())])

    result = ask(agent, "research x")

    tool_message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert "https://x.com" in tool_message.content


@pytest.mark.integration
def test_real_research_agent_searches_the_web_and_answers() -> None:
    """Runs the real agent (OpenRouter + Tavily) through the production dependency chain."""
    settings = Settings()
    if not (
        settings.openrouter_api_key.get_secret_value()
        and settings.tavily_api_key.get_secret_value()
    ):
        pytest.skip("DBAD_OPENROUTER_API_KEY and DBAD_TAVILY_API_KEY must be set")
    agent = deps.get_research_agent(
        deps.get_chat_model(settings),
        deps.get_web_search_tool(deps.get_tavily_client(settings)),
    )

    result = ask(agent, "Elon Musk")
    messages = result["messages"]

    # The model decided to search...
    searched = [call for m in messages if isinstance(m, AIMessage) for call in m.tool_calls]
    assert searched, "agent never called a tool"
    assert all(call["name"] == "web_search" for call in searched)

    # ...and the search really returned results (not an error payload).
    outputs = [
        WebSearchToolOutput.model_validate_json(m.content)
        for m in messages
        if isinstance(m, ToolMessage)
    ]
    assert outputs
    assert all(o.error is None for o in outputs), [o.error for o in outputs]
    assert all(o.results for o in outputs)

    # ...and the final answer is a substantive, grounded text, not an echo or a stub.
    final = messages[-1]
    assert isinstance(final, AIMessage)
    assert not final.tool_calls
    answer = str(final.text)
    assert len(answer) > 300
    assert "singer" in answer.lower()
    assert "http" in answer.lower(), "expected cited source URLs"
