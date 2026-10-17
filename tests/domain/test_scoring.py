import pytest

from dont_be_a_dick.domain.rubrics import R1, Dimension, Rubric
from dont_be_a_dick.domain.schemas import (
    DimensionScore,
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    PersonFacts,
    Role,
    Subject,
)
from dont_be_a_dick.domain.scoring import DEFAULT_CONFIG, ScoringConfig, compute_score

R5 = Rubric(
    id="R5",
    name="Counterweight",
    kind="counterweight",
    prompt_dir="r5",
    dimensions=(Dimension("C1", "Divestment", "Costly action that reduces risk"),),
)
R2 = Rubric(
    id="R2",
    name="Domination",
    kind="harm",
    prompt_dir="r2",
    dimensions=(Dimension("D1", "Suppression", "Suppressing dissent"),),
)

SUBJECT = Subject(name="Test Person")


def facts(
    seniority="executive", size="very_large", net_worth="unknown", office=None, voluntary=None
):
    return PersonFacts(
        roles=[Role(title="t", organization="o", seniority=seniority, voluntary=voluntary)],
        organization_size=size,
        net_worth=net_worth,
        highest_office=office,
    )


def item(n: int, tier: int = 1, dimension: str = "P1", rubric_id: str = "R1") -> EvidenceItem:
    return EvidenceItem(
        id=f"{rubric_id}-E{n:02d}",
        claim="c",
        dimension=dimension,
        quote="q",
        source_url="https://example.com",
        source_title="t",
        source_kind="news_report",
        source_tier=tier,
    )


def dossier(rubric_id="R1", n_items=3, tier=1, person_facts=None, dimension="P1") -> Dossier:
    return Dossier(
        rubric_id=rubric_id,
        subject=SUBJECT,
        items=[item(i + 1, tier, dimension, rubric_id) for i in range(n_items)],
        facts=person_facts or facts(),
    )


def verdict(rubric_id="R1", severity=2, dimension="P1", n_cited=1) -> JudgeVerdict:
    ids = [f"{rubric_id}-E{i + 1:02d}" for i in range(n_cited)] if severity else []
    return JudgeVerdict(
        rubric_id=rubric_id,
        insufficient_evidence=False,
        dimension_scores=[
            DimensionScore(dimension=dimension, severity=severity, evidence_ids=ids, rationale="r")
        ],
        rationale="overall",
    )


def insufficient(rubric_id="R1") -> JudgeVerdict:
    return JudgeVerdict(rubric_id=rubric_id, insufficient_evidence=True, rationale="thin")


def score_r1(severity: int, person_facts: PersonFacts | None = None, config=DEFAULT_CONFIG):
    return compute_score(
        [verdict(severity=severity)],
        [dossier(person_facts=person_facts)],
        [R1],
        config,
    )


@pytest.mark.parametrize(
    ("severity", "person_facts", "tier"),
    [
        (4, facts("founder_or_head_of_state", "very_large", "over_100b"), "ultimate"),
        (3, facts("executive", "very_large"), "major"),
        (2, facts("rank_and_file", "large"), "unwilling"),
        (1, facts("executive", "very_large"), "minor"),
        (0, facts("executive", "very_large"), "not_a_dick"),
    ],
)
def test_tiers(severity: int, person_facts: PersonFacts, tier: str) -> None:
    assert score_r1(severity, person_facts).tier == tier


def test_final_score_is_harm_times_influence() -> None:
    result = score_r1(3, facts("executive", "very_large"))

    assert result.harm_score == pytest.approx(0.7)
    assert result.final_score == pytest.approx(0.7 * result.influence)


def test_is_deterministic() -> None:
    assert score_r1(3) == score_r1(3)


def test_final_score_never_decreases_as_severity_rises() -> None:
    finals = [score_r1(s).final_score for s in range(5)]

    assert finals == sorted(finals)
    assert finals[0] == 0


def test_more_power_and_agency_never_lower_the_score() -> None:
    low = score_r1(3, facts("rank_and_file", "small")).final_score
    mid = score_r1(3, facts("manager", "large")).final_score
    high = score_r1(3, facts("founder_or_head_of_state", "very_large", "over_100b")).final_score

    assert low < mid < high


def test_involuntary_roles_lower_agency() -> None:
    free = score_r1(3, facts(voluntary=True))
    forced = score_r1(3, facts(voluntary=False))

    assert forced.agency < free.agency


def test_missing_roles_use_a_neutral_agency_and_say_so() -> None:
    result = compute_score(
        [verdict(severity=3)], [dossier(person_facts=PersonFacts())], [R1], DEFAULT_CONFIG
    )

    assert result.agency == DEFAULT_CONFIG.unknown_agency
    assert any("no roles documented" in n for n in result.notes)


def test_insufficient_r1_is_unrated() -> None:
    result = compute_score([insufficient()], [dossier()], [R1])

    assert result.tier == "unrated"
    assert result.final_score is None
    assert result.harm_score is None
    assert result.confidence == 0.0
    assert result.coverage == 0.0


def test_missing_r1_verdict_is_unrated() -> None:
    result = compute_score([], [], [R1])

    assert result.tier == "unrated"
    assert any("no verdict" in n for n in result.notes)


def test_a_failed_optional_rubric_lowers_coverage_but_still_rates() -> None:
    result = compute_score(
        [verdict("R1", 3)],
        [dossier("R1")],
        [R1, R5],
        DEFAULT_CONFIG,
    )

    assert result.tier != "unrated"
    assert result.coverage == 0.5


def test_harm_rubrics_combine_without_dilution() -> None:
    both = compute_score(
        [verdict("R1", 3), verdict("R2", 3, dimension="D1")],
        [dossier("R1"), dossier("R2", dimension="D1")],
        [R1, R2],
    )
    alone = compute_score([verdict("R1", 3)], [dossier("R1")], [R1])

    assert both.harm_score > alone.harm_score
    assert both.harm_score == pytest.approx(1 - (1 - 0.7) ** 2)


def test_a_zero_in_another_rubric_does_not_dilute_a_catastrophic_one() -> None:
    mixed = compute_score(
        [verdict("R1", 4), verdict("R2", 0, dimension="D1")],
        [dossier("R1"), dossier("R2", dimension="D1")],
        [R1, R2],
    )

    assert mixed.harm_score == pytest.approx(1.0)


def test_counterweight_only_reduces_and_respects_the_cap() -> None:
    base = compute_score([verdict("R1", 3)], [dossier("R1")], [R1, R5])
    with_counter = compute_score(
        [verdict("R1", 3), verdict("R5", 4, dimension="C1")],
        [dossier("R1"), dossier("R5", dimension="C1")],
        [R1, R5],
    )

    assert with_counter.final_score < base.final_score
    assert with_counter.counterweight_reduction == pytest.approx(DEFAULT_CONFIG.counterweight_cap)
    assert with_counter.final_score >= base.final_score * (1 - DEFAULT_CONFIG.counterweight_cap)


def test_counterweight_never_makes_a_zero_harm_score_negative() -> None:
    result = compute_score(
        [verdict("R1", 0), verdict("R5", 4, dimension="C1")],
        [dossier("R1"), dossier("R5", dimension="C1")],
        [R1, R5],
    )

    assert result.final_score == 0


def test_dimension_weights_change_the_score_through_config() -> None:
    config = ScoringConfig(dimension_weights={"P1": 0.5})

    weighted = score_r1(3, config=config)

    assert weighted.harm_score == pytest.approx(0.35)


def test_confidence_grows_with_better_and_more_evidence() -> None:
    def confidence(n_items: int, tier: int) -> float:
        return compute_score(
            [verdict(severity=3, n_cited=n_items)],
            [dossier(n_items=n_items, tier=tier)],
            [R1],
        ).confidence

    assert confidence(1, 1) < confidence(3, 1)
    assert confidence(3, 3) < confidence(3, 1)
    assert confidence(3, 1) == pytest.approx(1.0)


def test_confidence_ignores_what_the_judge_would_self_report() -> None:
    assert "confidence" not in JudgeVerdict.model_fields


def test_documented_zero_is_more_confident_than_undocumented_zero() -> None:
    documented = compute_score([verdict(severity=0)], [dossier(n_items=0)], [R1])
    undocumented = compute_score(
        [verdict(severity=0)], [dossier(n_items=0, person_facts=PersonFacts())], [R1]
    )

    assert documented.confidence > undocumented.confidence


def test_breakdown_reports_the_top_dimension_and_its_evidence() -> None:
    result = score_r1(3)

    [r1] = result.rubric_scores
    assert (r1.severity, r1.top_dimension, r1.evidence_ids) == (3, "P1", ["R1-E01"])
