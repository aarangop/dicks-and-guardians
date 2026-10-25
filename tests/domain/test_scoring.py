import pytest

from dont_be_a_dick.domain.rubrics import R1, Dimension, Rubric
from dont_be_a_dick.domain.schemas import (
    BenefitAttrs,
    DimensionScore,
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    PersonFacts,
    Role,
    Subject,
)
from dont_be_a_dick.domain.scoring import DEFAULT_CONFIG, ScoringConfig, compute_score

R2 = Rubric(
    id="R2",
    name="Domination",
    prompt_dir="r2",
    dimensions=(Dimension("D1", "Suppression", "Suppressing dissent"),),
)
R3 = Rubric(
    id="R3",
    name="Extraction",
    prompt_dir="r3",
    dimensions=(Dimension("X1", "Labor", "Wage theft"),),
)

SUBJECT = Subject(name="Test Person")


def facts(
    seniority="executive",
    size="very_large",
    net_worth="unknown",
    office=None,
    voluntary=None,
    reach="unknown",
    authority="unknown",
):
    return PersonFacts(
        reach=reach,
        authority=authority,
        roles=[Role(title="t", organization="o", seniority=seniority, voluntary=voluntary)],
        organization_size=size,
        net_worth=net_worth,
        highest_office=office,
    )


def item(
    n: int,
    tier: int = 1,
    dimension: str = "P1",
    rubric_id: str = "R1",
    benefit: BenefitAttrs | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        id=f"{rubric_id}-E{n:02d}",
        claim="c",
        dimension=dimension,
        polarity="benefit" if benefit is not None else "harm",
        benefit=benefit,
        quote="q",
        source_url="https://example.com",
        source_title="t",
        source_kind="news_report",
        source_tier=tier,
    )


def dossier(
    rubric_id="R1", n_items=3, tier=1, person_facts=None, dimension="P1", items=None
) -> Dossier:
    return Dossier(
        rubric_id=rubric_id,
        subject=SUBJECT,
        items=items
        if items is not None
        else [item(i + 1, tier, dimension, rubric_id) for i in range(n_items)],
        facts=person_facts or facts(),
    )


def verdict(rubric_id="R1", severity=2, dimension="P1", n_cited=1, polarity="harm") -> JudgeVerdict:
    ids = [f"{rubric_id}-E{i + 1:02d}" for i in range(n_cited)] if severity else []
    return JudgeVerdict(
        rubric_id=rubric_id,
        polarity=polarity,
        insufficient_evidence=False,
        dimension_scores=[
            DimensionScore(dimension=dimension, severity=severity, evidence_ids=ids, rationale="r")
        ],
        rationale="overall",
    )


def insufficient(rubric_id="R1", polarity="harm") -> JudgeVerdict:
    return JudgeVerdict(
        rubric_id=rubric_id, polarity=polarity, insufficient_evidence=True, rationale="thin"
    )


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


def test_a_head_of_state_outranks_a_global_ceo_in_power() -> None:
    head = score_r1(3, facts("founder_or_head_of_state", reach="global", authority="unilateral"))
    ceo = score_r1(3, facts("founder_or_head_of_state", reach="global", authority="none"))

    assert head.power == 1.0
    assert ceo.power < head.power
    assert ceo.final_score < head.final_score


def test_power_orders_by_reach_and_by_authority() -> None:
    def power(reach: str, authority: str) -> float:
        return score_r1(3, facts(reach=reach, authority=authority)).power

    reaches = ("organization", "industry", "national", "global")
    authorities = ("none", "shared", "unilateral")
    for authority in authorities:
        by_reach = [power(r, authority) for r in reaches]
        assert by_reach == sorted(by_reach)
    for reach in reaches:
        by_authority = [power(reach, a) for a in authorities]
        assert by_authority == sorted(by_authority)
    # above the unknown-power floor the readings are all distinct
    for reach in ("industry", "national", "global"):
        assert len({power(reach, a) for a in authorities}) == len(authorities)


def test_a_national_head_of_government_outranks_a_global_company_owner() -> None:
    state = score_r1(3, facts(reach="national", authority="unilateral", office="President"))
    company = score_r1(3, facts(reach="global", authority="none", net_worth="over_100b"))

    assert state.power > company.power


def test_an_unknown_authority_never_inflates_power() -> None:
    unknown = score_r1(3, facts(reach="global", authority="unknown")).power
    none = score_r1(3, facts(reach="global", authority="none")).power

    assert unknown == none


def test_wealth_and_size_alone_never_reach_the_top_of_the_scale() -> None:
    rich = score_r1(3, facts(size="very_large", net_worth="over_100b"))

    assert rich.power == DEFAULT_CONFIG.legacy_power_cap
    assert rich.power < 1.0


def test_a_documented_office_outranks_legacy_wealth_when_reach_is_unknown() -> None:
    office = score_r1(3, facts(size="small", office="Prime Minister"))
    rich = score_r1(3, facts(size="very_large", net_worth="over_100b"))

    assert office.power > rich.power


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
        [R1, R3],
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
    # strongest term plus the weaker one with diminishing returns: 0.7 + 0.25 * (1 - 0.7) * 0.7
    assert both.harm_score == pytest.approx(0.7 + DEFAULT_CONFIG.combine_rest_weight * 0.3 * 0.7)


def test_a_zero_in_another_rubric_does_not_dilute_a_catastrophic_one() -> None:
    mixed = compute_score(
        [verdict("R1", 4), verdict("R2", 0, dimension="D1")],
        [dossier("R1"), dossier("R2", dimension="D1")],
        [R1, R2],
    )

    assert mixed.harm_score == pytest.approx(1.0)


def test_many_small_terms_never_outweigh_one_major_term() -> None:
    major = compute_score([verdict("R1", 3)], [dossier("R1")], [R1])
    many_small = compute_score(
        [verdict("R1", 1), verdict("R2", 1, dimension="D1"), verdict("R3", 1, dimension="X1")],
        [dossier("R1"), dossier("R2", dimension="D1"), dossier("R3", dimension="X1")],
        [R1, R2, R3],
    )

    assert many_small.harm_score < major.harm_score


def benefit_score(severity: int, items=None, person_facts=None, config=DEFAULT_CONFIG):
    return compute_score(
        [verdict("R1", 2), verdict("R1", severity, polarity="benefit")],
        [dossier("R1", items=items, person_facts=person_facts)],
        [R1],
        config,
    )


def test_benefit_never_changes_the_harm_profile() -> None:
    without = compute_score([verdict("R1", 3)], [dossier("R1")], [R1])
    with_benefit = compute_score(
        [verdict("R1", 3), verdict("R1", 4, polarity="benefit")], [dossier("R1")], [R1]
    )

    assert with_benefit.harm_score == without.harm_score
    assert with_benefit.final_score == without.final_score
    assert with_benefit.tier == without.tier
    assert with_benefit.coverage == without.coverage
    assert with_benefit.confidence == without.confidence


def test_the_two_profiles_can_both_be_high() -> None:
    result = compute_score(
        [verdict("R1", 4), verdict("R1", 4, polarity="benefit")],
        [dossier("R1", person_facts=facts("founder_or_head_of_state", "very_large", "over_100b"))],
        [R1],
    )

    assert result.tier == "ultimate"
    assert result.benefit_tier == "ultimate_guardian"


def test_benefit_is_severity_times_influence() -> None:
    result = benefit_score(3, person_facts=facts("executive", "very_large"))

    assert result.benefit_score == pytest.approx(0.7 * result.influence)
    assert result.benefit_tier == "major_guardian"


def test_more_benefit_never_lowers_the_benefit_score() -> None:
    scores = [benefit_score(s).benefit_score for s in range(5)]

    assert scores == sorted(scores)
    assert scores[0] == 0


def test_documented_zero_benefit_is_not_a_negative() -> None:
    result = benefit_score(0)

    assert result.benefit_tier == "none_documented"
    assert result.benefit_score == 0
    assert result.tier == compute_score([verdict("R1", 2)], [dossier("R1")], [R1]).tier


@pytest.mark.parametrize("severity", [1, 2])
def test_a_documented_benefit_never_reads_as_none_documented(severity) -> None:
    # A junior person's role-based score is below the Minor cut, but the act is documented.
    result = benefit_score(severity, person_facts=facts("rank_and_file", "small"))

    assert result.benefit_score < DEFAULT_CONFIG.benefit_tier_minor
    assert result.benefit_tier == "minor_guardian"


def test_the_minor_floor_does_not_lift_higher_tiers_or_zero() -> None:
    zero = benefit_score(0, person_facts=facts("rank_and_file", "small"))
    major = benefit_score(3, person_facts=facts("executive", "very_large"))

    assert zero.benefit_tier == "none_documented"
    assert major.benefit_tier == "major_guardian"


@pytest.mark.parametrize("benefit_verdicts", [[], [insufficient("R1", "benefit")]])
def test_missing_or_insufficient_benefit_is_unrated_and_leaves_harm_alone(
    benefit_verdicts,
) -> None:
    result = compute_score([verdict("R1", 3), *benefit_verdicts], [dossier("R1")], [R1])

    assert result.benefit_tier == "unrated"
    assert result.benefit_score is None
    assert result.tier == "major"
    assert any(n.startswith("R1 benefit:") for n in result.notes)


def test_benefit_is_still_scored_when_harm_is_unrated() -> None:
    result = compute_score(
        [insufficient("R1"), verdict("R1", 3, polarity="benefit")], [dossier("R1")], [R1]
    )

    assert result.tier == "unrated"
    assert result.benefit_score is not None
    assert result.benefit_tier != "unrated"


def test_rubrics_without_a_benefit_side_ignore_benefit_verdicts() -> None:
    result = compute_score(
        [
            verdict("R1", 2),
            verdict("R2", 2, dimension="D1"),
            verdict("R2", 4, dimension="D1", polarity="benefit"),
        ],
        [dossier("R1"), dossier("R2", dimension="D1")],
        [R1, R2],
    )

    assert [s.rubric_id for s in result.benefit_scores] == ["R1"]


def test_dimension_weights_apply_to_harm_only() -> None:
    weighted = ScoringConfig(dimension_weights={"P1": 0.5})

    assert benefit_score(3, config=weighted).benefit_score == benefit_score(3).benefit_score
    assert benefit_score(3, config=weighted).harm_score < benefit_score(3).harm_score


def test_benefit_confidence_grows_with_better_evidence() -> None:
    strong = benefit_score(3, items=[item(i + 1) for i in range(3)])
    weak = benefit_score(3, items=[item(1, tier=3)])

    assert weak.benefit_confidence < strong.benefit_confidence


ROLE_FACTS = facts("rank_and_file", "small")


def test_acting_against_the_role_gives_high_agency_to_that_act() -> None:
    plain = benefit_score(3, items=[item(1)], person_facts=ROLE_FACTS)
    defiant = benefit_score(
        3, items=[item(1, benefit=BenefitAttrs(against_role=True))], person_facts=ROLE_FACTS
    )

    cfg = DEFAULT_CONFIG
    expected = (
        0.7 * cfg.against_role_agency * (cfg.power_floor + (1 - cfg.power_floor) * defiant.power)
    )
    assert defiant.benefit_score == pytest.approx(expected)
    assert defiant.benefit_score > plain.benefit_score
    assert plain.benefit_score == pytest.approx(0.7 * plain.influence)
    assert any("against role" in n for n in defiant.notes)


def test_acting_against_the_role_never_lowers_agency() -> None:
    boss = facts("founder_or_head_of_state", "very_large")
    plain = benefit_score(3, items=[item(1)], person_facts=boss)
    defiant = benefit_score(
        3, items=[item(1, benefit=BenefitAttrs(against_role=True))], person_facts=boss
    )

    assert defiant.benefit_score == pytest.approx(plain.benefit_score)


def test_an_attributed_outcome_lifts_power() -> None:
    outcome = BenefitAttrs(outcome_scale="very_large", outcome_attributed=True)
    plain = benefit_score(3, items=[item(1)], person_facts=ROLE_FACTS)
    lifted = benefit_score(3, items=[item(1, benefit=outcome)], person_facts=ROLE_FACTS)

    assert lifted.benefit_score > plain.benefit_score
    assert any("power lifted" in n for n in lifted.notes)
    # the harm profile still uses the role-based power
    assert lifted.influence == plain.influence


@pytest.mark.parametrize(
    "attrs",
    [
        BenefitAttrs(outcome_scale="very_large", outcome_attributed=False),
        BenefitAttrs(outcome_scale="unknown", outcome_attributed=True),
    ],
    ids=["unattributed", "unknown-scale"],
)
def test_an_outcome_that_is_unattributed_or_unsized_changes_nothing(attrs) -> None:
    plain = benefit_score(3, items=[item(1)], person_facts=ROLE_FACTS)
    claimed = benefit_score(3, items=[item(1, benefit=attrs)], person_facts=ROLE_FACTS)

    assert claimed.benefit_score == pytest.approx(plain.benefit_score)


def test_an_outcome_cited_only_from_a_weak_source_changes_nothing() -> None:
    outcome = BenefitAttrs(outcome_scale="very_large", outcome_attributed=True)
    plain = benefit_score(3, items=[item(1, tier=3)], person_facts=ROLE_FACTS)
    claimed = benefit_score(3, items=[item(1, tier=3, benefit=outcome)], person_facts=ROLE_FACTS)

    assert claimed.benefit_score == pytest.approx(plain.benefit_score)


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
