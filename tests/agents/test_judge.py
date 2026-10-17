from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from dont_be_a_dick.agents.judge import MAX_ATTEMPTS, LangChainJudge
from dont_be_a_dick.domain.evidence import VerdictError, build_dossier
from dont_be_a_dick.domain.rubrics import R1
from dont_be_a_dick.domain.schemas import (
    Finding,
    ResearchFindings,
    Role,
    Subject,
)

SUBJECT = Subject(name="Test Person")


class FakeToolCallingModel(GenericFakeChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeToolCallingModel":
        return self


def verdict_call(*scores: dict, insufficient: bool = False) -> AIMessage:
    args = {
        "rubric_id": "R1",
        "insufficient_evidence": insufficient,
        "dimension_scores": list(scores),
        "rationale": "overall",
    }
    return AIMessage(content="", tool_calls=[{"name": "JudgeVerdict", "args": args, "id": "1"}])


def score(dimension="P1", severity=2, ids=("R1-E01",)) -> dict:
    return {
        "dimension": dimension,
        "severity": severity,
        "evidence_ids": list(ids),
        "rationale": "anchor 2",
    }


@pytest.fixture
def dossier():
    finding = Finding(
        claim="Disbanded the safety team",
        dimension="P1",
        quote="q",
        source_url="https://example.com/a",
        source_title="A",
        source_kind="news_report",
    )
    return build_dossier(SUBJECT, R1, ResearchFindings(findings=[finding]))


def judge_with(*messages: AIMessage) -> LangChainJudge:
    return LangChainJudge(FakeToolCallingModel(messages=iter(messages)), prompt_for=lambda r: "p")


@pytest.mark.anyio
async def test_returns_a_valid_verdict(dossier) -> None:
    judge = judge_with(verdict_call(score()))

    verdict = await judge.judge(dossier, R1)

    assert verdict.dimension_scores[0].severity == 2
    assert verdict.dimension_scores[0].evidence_ids == ["R1-E01"]


@pytest.mark.anyio
async def test_retries_once_when_the_verdict_cites_unknown_evidence(dossier) -> None:
    judge = judge_with(verdict_call(score(ids=("R1-E99",))), verdict_call(score()))

    verdict = await judge.judge(dossier, R1)

    assert verdict.dimension_scores[0].evidence_ids == ["R1-E01"]


@pytest.mark.anyio
async def test_retries_when_the_structure_is_invalid(dossier) -> None:
    invalid = verdict_call(score(severity=3, ids=()))
    judge = judge_with(invalid, verdict_call(score()))

    verdict = await judge.judge(dossier, R1)

    assert verdict.dimension_scores[0].severity == 2


@pytest.mark.anyio
async def test_gives_up_after_max_attempts(dossier) -> None:
    bad = [verdict_call(score(ids=("R1-E99",))) for _ in range(MAX_ATTEMPTS)]
    judge = judge_with(*bad)

    with pytest.raises(VerdictError) as exc:
        await judge.judge(dossier, R1)

    assert any("unknown evidence id" in p for p in exc.value.problems)


@pytest.mark.anyio
async def test_empty_dossier_is_insufficient_without_calling_the_model() -> None:
    empty = build_dossier(SUBJECT, R1, ResearchFindings())
    judge = judge_with()  # any model call would exhaust the iterator and fail

    verdict = await judge.judge(empty, R1)

    assert verdict.insufficient_evidence is True
    assert verdict.dimension_scores == []


@pytest.mark.anyio
async def test_roles_alone_are_enough_to_ask_the_model_for_a_zero() -> None:
    facts = ResearchFindings(
        facts={
            "roles": [
                Role(
                    title="Professor", organization="A University", seniority="manager"
                ).model_dump()
            ]
        }
    )
    dossier = build_dossier(SUBJECT, R1, facts)
    judge = judge_with(verdict_call(score(severity=0, ids=())))

    verdict = await judge.judge(dossier, R1)

    assert verdict.dimension_scores[0].severity == 0
