from datetime import date
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from dont_be_a_dick.agents.researcher import LangChainResearcher, ResearchBudget, ResearchError
from dont_be_a_dick.domain.rubrics import R1
from dont_be_a_dick.domain.schemas import Subject

SUBJECT = Subject(name="Test Person", descriptor="CEO of ExampleCorp")

FINDINGS = {
    "findings": [
        {
            "claim": "Disbanded the safety team",
            "dimension": "P1",
            "quote": "we disbanded the team",
            "source_url": "https://example.com/a",
            "source_title": "A",
            "source_kind": "news_report",
            "event_date": date(2024, 5, 1).isoformat(),
        },
        {
            "claim": "Op-ed against regulation",
            "dimension": "P9",
            "quote": "q",
            "source_url": "https://example.com/b",
            "source_title": "B",
            "source_kind": "opinion_or_advocacy",
        },
    ],
    "facts": {"highest_office": "CEO"},
    "gaps": [],
}


class FakeToolCallingModel(GenericFakeChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCallingModel":
        return self


def scripted(*messages: AIMessage) -> FakeToolCallingModel:
    return FakeToolCallingModel(messages=iter(messages))


def call(name: str, args: dict, id_: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id_}])


@pytest.fixture
def searches() -> list[str]:
    return []


@pytest.fixture
def web_search(searches: list[str]):
    @tool
    def web_search(query: str) -> str:
        """Search the web."""
        searches.append(query)
        return "result text"

    return web_search


@pytest.mark.anyio
async def test_research_runs_tools_and_builds_a_dossier(web_search, searches) -> None:
    model = scripted(
        call("web_search", {"query": "test person"}, "1"),
        call("ResearchFindings", FINDINGS, "2"),
    )
    researcher = LangChainResearcher(model, [web_search])

    dossier = await researcher.research(SUBJECT, R1)

    assert searches == ["test person"]
    assert dossier.rubric_id == "R1"
    assert dossier.subject == SUBJECT
    assert [i.id for i in dossier.items] == ["R1-E01"]
    assert dossier.items[0].source_tier == 2
    assert any("unknown dimension" in g for g in dossier.gaps)
    assert dossier.facts.highest_office == "CEO"


@pytest.mark.anyio
async def test_queries_run_come_from_the_search_calls_not_the_model(web_search) -> None:
    model = scripted(
        call("web_search", {"query": "first"}, "1"),
        call("web_search", {"query": "second"}, "2"),
        call("ResearchFindings", FINDINGS, "3"),
    )

    dossier = await LangChainResearcher(model, [web_search]).research(SUBJECT, R1)

    assert dossier.queries_run == ["first", "second"]


@pytest.mark.anyio
async def test_a_result_that_omits_a_field_is_sent_back_for_another_try(web_search) -> None:
    partial = {"facts": {"highest_office": "CEO"}}  # no findings, no gaps
    model = scripted(
        call("ResearchFindings", partial, "1"), call("ResearchFindings", FINDINGS, "2")
    )

    dossier = await LangChainResearcher(model, [web_search]).research(SUBJECT, R1)

    assert [i.id for i in dossier.items] == ["R1-E01"]


@pytest.mark.anyio
async def test_research_with_no_findings_is_a_valid_empty_dossier(web_search) -> None:
    empty = {"findings": [], "facts": {}, "gaps": ["nothing found"]}
    researcher = LangChainResearcher(scripted(call("ResearchFindings", empty, "1")), [web_search])

    dossier = await researcher.research(SUBJECT, R1)

    assert dossier.items == []
    assert dossier.gaps == ["nothing found"]


@pytest.mark.anyio
async def test_research_without_structured_output_raises(web_search) -> None:
    researcher = LangChainResearcher(scripted(AIMessage(content="I give up")), [web_search])

    with pytest.raises(ResearchError):
        await researcher.research(SUBJECT, R1)


@pytest.mark.anyio
async def test_system_prompt_comes_from_the_injected_provider(web_search) -> None:
    seen: list[str] = []

    def prompt_for(rubric):
        seen.append(rubric.id)
        return "custom prompt"

    researcher = LangChainResearcher(
        scripted(call("ResearchFindings", {"findings": [], "facts": {}, "gaps": []}, "1")),
        [web_search],
        prompt_for=prompt_for,
    )

    await researcher.research(SUBJECT, R1)

    assert seen == ["R1"]


def test_budget_sets_the_recursion_limit() -> None:
    assert ResearchBudget(searches=10, fetches=5).recursion_limit == 80
    assert ResearchBudget(searches=20, fetches=10).recursion_limit == 140


@pytest.mark.anyio
async def test_searches_past_the_budget_are_refused_and_the_agent_still_finishes(
    web_search, searches
) -> None:
    model = scripted(
        call("web_search", {"query": "one"}, "1"),
        call("web_search", {"query": "two"}, "2"),
        call("web_search", {"query": "three"}, "3"),
        call("ResearchFindings", FINDINGS, "4"),
    )
    researcher = LangChainResearcher(
        model, [web_search], budget=ResearchBudget(searches=2, fetches=1)
    )

    dossier = await researcher.research(SUBJECT, R1)

    assert searches == ["one", "two"]
    assert dossier.items


def test_the_budget_is_stated_in_the_system_prompt(web_search) -> None:
    researcher = LangChainResearcher(
        scripted(), [web_search], budget=ResearchBudget(searches=4, fetches=2)
    )

    assert "4 searches and 2 fetches" in researcher._budgeted_prompt(R1)
