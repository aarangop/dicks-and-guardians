from datetime import date

import pytest

from dont_be_a_dick.domain.evidence import build_dossier, check_verdict, classify_tier
from dont_be_a_dick.domain.rubrics import R1
from dont_be_a_dick.domain.schemas import (
    DimensionScore,
    Finding,
    JudgeVerdict,
    PersonFacts,
    ResearchFindings,
    Subject,
)

SUBJECT = Subject(name="Test Person")


def finding(**overrides) -> Finding:
    data = {
        "claim": "Dissolved the safety team",
        "dimension": "P1",
        "quote": "we disbanded the team",
        "source_url": "https://example.com/a",
        "source_title": "A",
        "source_kind": "news_report",
        "event_date": date(2024, 5, 1),
    }
    return Finding(**{**data, **overrides})


@pytest.mark.parametrize(
    ("kind", "url", "tier"),
    [
        ("court_record", "https://example.com/x", 1),
        ("investigative_journalism", "https://example.com/x", 2),
        ("news_report", "https://example.com/x", 2),
        ("opinion_or_advocacy", "https://example.com/x", 3),
        ("other", "https://example.com/x", 3),
        ("news_report", "https://www.sec.gov/filing", 1),
        ("other", "https://courtlistener.com/opinion/1", 1),
        ("opinion_or_advocacy", "https://whitehouse.gov/blog", 3),
    ],
)
def test_classify_tier(kind: str, url: str, tier: int) -> None:
    assert classify_tier(kind, url) == tier  # type: ignore[arg-type]


def test_build_dossier_assigns_sequential_ids_and_tiers() -> None:
    research = ResearchFindings(
        findings=[
            finding(),
            finding(claim="Lobbied against regulation", source_kind="opinion_or_advocacy"),
        ],
        facts=PersonFacts(),
        gaps=[],
    )

    dossier = build_dossier(SUBJECT, R1, research)

    assert [i.id for i in dossier.items] == ["R1-E01", "R1-E02"]
    assert [i.source_tier for i in dossier.items] == [2, 3]


def test_build_dossier_drops_duplicates_and_unknown_dimensions() -> None:
    research = ResearchFindings(
        findings=[finding(), finding(), finding(dimension="P9")], facts=PersonFacts(), gaps=[]
    )

    dossier = build_dossier(SUBJECT, R1, research)

    assert len(dossier.items) == 1
    assert any("unknown dimension" in gap for gap in dossier.gaps)


def verdict(*scores: DimensionScore, rubric_id: str = "R1") -> JudgeVerdict:
    return JudgeVerdict(
        rubric_id=rubric_id,
        insufficient_evidence=False,
        dimension_scores=list(scores),
        rationale="x",
    )


def dim(dimension: str = "P1", severity: int = 2, ids=("R1-E01",)) -> DimensionScore:
    return DimensionScore(
        dimension=dimension, severity=severity, evidence_ids=list(ids), rationale="r"
    )


@pytest.fixture
def dossier():
    return build_dossier(
        SUBJECT,
        R1,
        ResearchFindings(
            findings=[
                finding(),
                finding(
                    claim="Op-ed", source_kind="opinion_or_advocacy", source_url="https://b.com"
                ),
            ],
            facts=PersonFacts(),
            gaps=[],
        ),
    )


def test_sound_verdict_has_no_problems(dossier) -> None:
    assert check_verdict(verdict(dim()), dossier, R1) == []


def test_unknown_evidence_id_is_a_problem(dossier) -> None:
    problems = check_verdict(verdict(dim(ids=("R1-E99",))), dossier, R1)

    assert any("unknown evidence id" in p for p in problems)


def test_unknown_dimension_is_a_problem(dossier) -> None:
    problems = check_verdict(verdict(dim("P9")), dossier, R1)

    assert any("unknown dimension" in p for p in problems)


def test_severity_resting_only_on_tier_3_is_a_problem(dossier) -> None:
    problems = check_verdict(verdict(dim(ids=("R1-E02",))), dossier, R1)

    assert any("tier-3" in p for p in problems)


def test_tier_3_alongside_better_evidence_is_fine(dossier) -> None:
    assert check_verdict(verdict(dim(ids=("R1-E01", "R1-E02"))), dossier, R1) == []


def test_wrong_rubric_id_is_a_problem(dossier) -> None:
    problems = check_verdict(verdict(dim(), rubric_id="R2"), dossier, R1)

    assert any("expected 'R1'" in p for p in problems)
