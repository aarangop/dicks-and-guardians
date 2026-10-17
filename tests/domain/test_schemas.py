import pytest
from pydantic import TypeAdapter, ValidationError

from dont_be_a_dick.domain.schemas import (
    Ambiguous,
    DimensionScore,
    JudgeVerdict,
    NeedsDisambiguation,
    Refused,
    Resolution,
    Resolved,
    ScoreOutcome,
    Subject,
)


def score(dimension: str = "P1", severity: int = 2, ids: tuple[str, ...] = ("R1-E01",)):
    return DimensionScore(
        dimension=dimension, severity=severity, evidence_ids=list(ids), rationale="because"
    )


def test_severity_of_one_or_more_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="cites no evidence"):
        score(severity=1, ids=())


def test_severity_zero_needs_no_evidence() -> None:
    assert score(severity=0, ids=()).severity == 0


@pytest.mark.parametrize("severity", [-1, 5])
def test_severity_is_bounded(severity: int) -> None:
    with pytest.raises(ValidationError):
        score(severity=severity)


def test_insufficient_evidence_verdict_must_have_no_scores() -> None:
    with pytest.raises(ValidationError, match="must not include scores"):
        JudgeVerdict(
            rubric_id="R1",
            insufficient_evidence=True,
            dimension_scores=[score()],
            rationale="x",
        )


def test_rated_verdict_needs_at_least_one_score() -> None:
    with pytest.raises(ValidationError, match="at least one dimension score"):
        JudgeVerdict(rubric_id="R1", insufficient_evidence=False, rationale="x")


def test_dimension_scored_at_most_once() -> None:
    with pytest.raises(ValidationError, match="at most once"):
        JudgeVerdict(
            rubric_id="R1",
            insufficient_evidence=False,
            dimension_scores=[score("P1"), score("P1")],
            rationale="x",
        )


def test_insufficient_evidence_verdict_is_valid() -> None:
    verdict = JudgeVerdict(rubric_id="R1", insufficient_evidence=True, rationale="no data")

    assert verdict.dimension_scores == []


def test_ambiguous_needs_two_candidates() -> None:
    with pytest.raises(ValidationError):
        Ambiguous(candidates=[Subject(name="Peter Singer")])


def test_resolution_round_trips_through_its_discriminator() -> None:
    adapter = TypeAdapter(Resolution)
    for original in (
        Resolved(subject=Subject(name="A", descriptor="b")),
        Ambiguous(
            candidates=[Subject(name="A", descriptor="x"), Subject(name="A", descriptor="y")]
        ),
        Refused(reason="private individual"),
    ):
        assert adapter.validate_python(original.model_dump()) == original


def test_outcome_round_trips_through_its_discriminator() -> None:
    adapter = TypeAdapter(ScoreOutcome)
    outcome = NeedsDisambiguation(candidates=[Subject(name="A", descriptor="x")])

    assert adapter.validate_python(outcome.model_dump()) == outcome
