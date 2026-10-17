from datetime import date
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from dont_be_a_dick.agents.researcher import LangChainResearcher, ResearchError
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
    "queries_run": ["test person safety team"],
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
async def test_research_with_no_findings_is_a_valid_empty_dossier(web_search) -> None:
    empty = {"findings": [], "gaps": ["nothing found"]}
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
        scripted(call("ResearchFindings", {"findings": []}, "1")),
        [web_search],
        prompt_for=prompt_for,
    )

    await researcher.research(SUBJECT, R1)

    assert seen == ["R1"]
