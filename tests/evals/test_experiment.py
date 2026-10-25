import pytest

from dont_be_a_dick.domain.rubrics import R1
from dont_be_a_dick.domain.schemas import JudgeVerdict
from dont_be_a_dick.evals import experiment as exp
from dont_be_a_dick.evals.golden import GOLDEN_DIR, load_cases

EXPECTED = {"tier": "major", "final_score": 0.5, "severities": {"R1": {"a": 3, "b": 1}}}


def test_tier_match() -> None:
    assert exp.tier_match(output={"tier": "major"}, expected_output=EXPECTED).value == 1.0
    assert exp.tier_match(output={"tier": "minor"}, expected_output=EXPECTED).value == 0.0


def test_severity_mae_penalises_missing_dimensions() -> None:
    output = {"severities": {"R1": {"a": 2}}}  # off by one on a, b missing

    result = exp.severity_mae(output=output, expected_output=EXPECTED)

    assert result is not None
    assert result.value == pytest.approx((1 + exp.MAX_SEVERITY) / 2)


def test_score_and_severity_evaluators_skip_when_nothing_is_expected() -> None:
    bare = {"tier": "minor", "final_score": None, "severities": {}}

    assert exp.score_error(output={"final_score": 0.1}, expected_output=bare) is None
    assert exp.severity_mae(output={"severities": {}}, expected_output=bare) is None


class FakeJudge:
    async def judge(self, dossier, rubric, polarity="harm"):
        return JudgeVerdict(
            rubric_id=rubric.id,
            polarity=polarity,
            dimension_scores=[],
            insufficient_evidence=True,
            rationale="fake",
        )


@pytest.mark.anyio
async def test_judge_case_scores_the_dossiers_it_is_given() -> None:
    case = load_cases()[0]

    output = await exp.judge_case(FakeJudge(), case.dossiers, [R1])  # type: ignore[arg-type]

    assert output["tier"] == "unrated"
    assert output["failures"] == []


def test_golden_cases_load_and_reference_known_dimensions() -> None:
    cases = load_cases(GOLDEN_DIR)

    assert cases
    for case in cases:
        assert case.expected.tier
        for rubric_id, dims in case.expected.severities.items():
            assert rubric_id in {d.rubric_id for d in case.dossiers}
            assert all(0 <= s <= exp.MAX_SEVERITY for s in dims.values())
