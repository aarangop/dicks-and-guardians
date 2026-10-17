from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from pydantic import Field

from dont_be_a_dick.agents.resolver import (
    LangChainSubjectResolver,
    ResolutionDecision,
    ResolutionError,
    to_resolution,
)
from dont_be_a_dick.agents.summarizer import LangChainSummarizer
from dont_be_a_dick.domain.schemas import (
    Ambiguous,
    EvidenceItem,
    Refused,
    Resolved,
    ScoreBreakdown,
    Subject,
)


class FakeToolCallingModel(GenericFakeChatModel):
    seen: list[Any] = Field(default_factory=list)

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCallingModel":
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(messages)
        return super()._generate(messages, *args, **kwargs)


def scripted(*messages: AIMessage) -> FakeToolCallingModel:
    return FakeToolCallingModel(messages=iter(messages))


def decision_call(**args: Any) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": "ResolutionDecision", "args": args, "id": "1"}]
    )


@pytest.fixture
def web_search():
    @tool
    def web_search(query: str) -> str:
        """Search the web."""
        return "results"

    return web_search


# --- summarizer -------------------------------------------------------------


@pytest.mark.anyio
async def test_summarizer_returns_text_and_sends_evidence_ids_to_the_model() -> None:
    model = scripted(AIMessage(content="  Major Dick because of [R1-E01].  "))
    breakdown = ScoreBreakdown(
        rubric_scores=[],
        power=0.5,
        agency=0.5,
        influence=0.5,
        harm_score=0.7,
        counterweight_reduction=0,
        final_score=0.35,
        tier="minor",
        coverage=1,
        confidence=0.8,
    )
    evidence = [
        EvidenceItem(
            id="R1-E01",
            claim="Disbanded the safety team",
            dimension="P1",
            quote="q",
            source_url="https://example.com/a",
            source_title="A",
            source_kind="news_report",
            source_tier=2,
        )
    ]

    summary = await LangChainSummarizer(model, prompt="p").summarize(
        Subject(name="Test Person"), breakdown, evidence
    )

    assert summary == "Major Dick because of [R1-E01]."
    system, human = model.seen[0]
    assert system.content == "p"
    assert "R1-E01" in human.content
    assert "https://example.com/a" in human.content
    assert "quote" not in human.content  # raw quotes are not needed for the summary


# --- resolver ---------------------------------------------------------------


@pytest.mark.anyio
async def test_resolver_resolves_a_single_public_figure(web_search) -> None:
    model = scripted(
        decision_call(
            outcome="resolved",
            candidates=[{"name": "Peter Singer", "descriptor": "Australian moral philosopher"}],
        )
    )

    resolution = await LangChainSubjectResolver(model, [web_search]).resolve(
        "Peter Singer", "philosopher"
    )

    assert resolution == Resolved(
        subject=Subject(name="Peter Singer", descriptor="Australian moral philosopher")
    )
    request = model.seen[0][-1].content
    assert "Name: Peter Singer" in request
    assert "Descriptor: philosopher" in request


@pytest.mark.anyio
async def test_resolver_reports_ambiguity(web_search) -> None:
    model = scripted(
        decision_call(
            outcome="ambiguous",
            candidates=[
                {"name": "Peter Singer", "descriptor": "philosopher"},
                {"name": "Peter Singer", "descriptor": "strategist"},
            ],
        )
    )

    resolution = await LangChainSubjectResolver(model, [web_search]).resolve("Peter Singer")

    assert isinstance(resolution, Ambiguous)
    assert [c.descriptor for c in resolution.candidates] == ["philosopher", "strategist"]


@pytest.mark.anyio
async def test_resolver_refuses_private_individuals(web_search) -> None:
    model = scripted(decision_call(outcome="refused", reason="No notable public figure matches."))

    resolution = await LangChainSubjectResolver(model, [web_search]).resolve("Jane Q. Nobody")

    assert resolution == Refused(reason="No notable public figure matches.")


@pytest.mark.parametrize(
    "decision",
    [
        ResolutionDecision(outcome="resolved"),
        ResolutionDecision(
            outcome="resolved", candidates=[Subject(name="A"), Subject(name="A", descriptor="b")]
        ),
        ResolutionDecision(outcome="ambiguous", candidates=[Subject(name="A")]),
        ResolutionDecision(outcome="refused"),
    ],
)
def test_inconsistent_decisions_are_rejected(decision: ResolutionDecision) -> None:
    with pytest.raises(ResolutionError):
        to_resolution(decision)
