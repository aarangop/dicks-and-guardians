"""Deterministic scoring: judge verdicts + extracted facts in, `ScoreBreakdown` out.

Pure functions, no I/O, no LLM. The same inputs always give the same output
(rubric principle 2). Every number lives in `ScoringConfig`, so calibration
means changing config, not code. The defaults are a first guess to be tuned.

How it works:
1. Per rubric and side, severity per dimension -> strength in 0-1 (`severity_strength`),
   take the max over dimensions so one catastrophic act is not diluted.
2. Within a side, rubrics combine max-dominant: the strongest term, plus the others with
   diminishing returns (`combine_rest_weight`). Never an average, never a plain sum.
3. Harm is multiplied by influence (agency x power), so rank and file rank lower.
4. The benefit side is scored independently from its own verdicts, with the same combination.
   Its influence is per act: an act against the role's expectations has high agency, and a
   documented, attributed outcome can lift power. Benefit is never netted against harm.
5. Missing required harm rubrics give `unrated`. Coverage and confidence are computed
   from what was usable, not self-reported by judges.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    DimensionScore,
    Dossier,
    GuardianTier,
    JudgeVerdict,
    PersonFacts,
    RubricScore,
    ScoreBreakdown,
    Tier,
)


def _default_severity_strength() -> dict[int, float]:
    return {0: 0.0, 1: 0.15, 2: 0.4, 3: 0.7, 4: 1.0}


@dataclass(frozen=True)
class ScoringConfig:
    severity_strength: Mapping[int, float] = field(default_factory=_default_severity_strength)
    rubric_weights: Mapping[str, float] = field(default_factory=dict)
    """Per-rubric weight in the harm OR. Missing means 1.0."""
    dimension_weights: Mapping[str, float] = field(default_factory=dict)
    """Per-dimension weight (for example to weight pathways). Missing means 1.0."""
    required_rubric_ids: tuple[str, ...] = ("R1", "R2")
    """If one of these is among the rubrics but has no usable verdict, the result is unrated."""

    seniority_agency: Mapping[str, float] = field(
        default_factory=lambda: {
            "rank_and_file": 0.25,
            "manager": 0.5,
            "executive": 0.85,
            "founder_or_head_of_state": 1.0,
        }
    )
    involuntary_agency_factor: float = 0.5
    unknown_agency: float = 0.5

    size_power: Mapping[str, float] = field(
        default_factory=lambda: {"unknown": 0.3, "small": 0.2, "large": 0.6, "very_large": 0.9}
    )
    net_worth_power: Mapping[str, float] = field(
        default_factory=lambda: {
            "unknown": 0.3,
            "under_10m": 0.1,
            "10m_to_1b": 0.5,
            "1b_to_100b": 0.85,
            "over_100b": 1.0,
        }
    )
    office_power: float = 0.9
    """Reading for a documented highest office when reach is unknown. It sits above every
    legacy wealth or size reading, because holding the office is the stronger claim."""
    legacy_power_cap: float = 0.85
    """Ceiling for the size and net worth readings, used only when reach is unknown. Wealth or
    a large organization alone never reaches the top of the scale."""
    reach_power: Mapping[str, Mapping[str, float]] = field(
        default_factory=lambda: {
            "organization": {"none": 0.2, "shared": 0.3, "unilateral": 0.4},
            "industry": {"none": 0.45, "shared": 0.55, "unilateral": 0.65},
            "national": {"none": 0.65, "shared": 0.75, "unilateral": 0.9},
            "global": {"none": 0.85, "shared": 0.9, "unilateral": 1.0},
        }
    )
    """Power by reach, then by authority. Binding people who did not consent (law, force) is
    worth more than persuading or selling to people who can say no. An unknown authority is
    read as `none`, the lowest, so a missing fact never inflates power."""
    power_floor: float = 0.4
    """Even a powerless person keeps this share of the influence multiplier."""

    combine_rest_weight: float = 0.25
    """How much the weaker terms of a side add on top of the strongest one."""

    against_role_agency: float = 1.0
    """Agency for a benefit act that went against the role's expectations (refusal, disclosure)."""
    outcome_max_source_tier: int = 2
    """Weakest source tier that can lift a benefit act's power through a documented outcome."""

    tier_ultimate: float = 0.75
    tier_major: float = 0.45
    tier_minor: float = 0.1
    unwilling_min_harm: float = 0.4
    unwilling_max_influence: float = 0.3

    benefit_tier_ultimate: float = 0.75
    benefit_tier_major: float = 0.45
    benefit_tier_minor: float = 0.1

    tier_quality: Mapping[int, float] = field(default_factory=lambda: {1: 1.0, 2: 0.7, 3: 0.3})
    evidence_target: float = 3.0
    """Quality-weighted items needed for full confidence in one rubric."""
    documented_zero_confidence: float = 0.5
    undocumented_zero_confidence: float = 0.25


DEFAULT_CONFIG = ScoringConfig()


# --- helpers ----------------------------------------------------------------


def _dimension_strength(score: DimensionScore, config: ScoringConfig) -> float:
    return config.severity_strength[score.severity] * config.dimension_weights.get(
        score.dimension, 1.0
    )


def _strength(verdict: JudgeVerdict, config: ScoringConfig) -> float:
    return max((_dimension_strength(s, config) for s in verdict.dimension_scores), default=0.0)


def _usable(verdict: JudgeVerdict | None) -> bool:
    return verdict is not None and not verdict.insufficient_evidence


def _merge_facts(dossiers: Sequence[Dossier]) -> list[PersonFacts]:
    return [d.facts for d in dossiers]


def _agency(facts: Sequence[PersonFacts], config: ScoringConfig) -> tuple[float, bool]:
    roles = [r for f in facts for r in f.roles]
    if not roles:
        return config.unknown_agency, False
    values = [
        config.seniority_agency[r.seniority]
        * (config.involuntary_agency_factor if r.voluntary is False else 1.0)
        for r in roles
    ]
    return max(values), True


def _power(facts: Sequence[PersonFacts], config: ScoringConfig) -> float:
    """Highest reading across all facts.

    With a known reach, power is `reach_power[reach][authority]`. Without one, fall back to
    the size and net worth readings (capped), and to a documented highest office.
    """
    candidates = [config.size_power["unknown"], config.net_worth_power["unknown"]]
    for f in facts:
        if f.reach != "unknown":
            authority = "none" if f.authority == "unknown" else f.authority
            candidates.append(config.reach_power[f.reach][authority])
            continue
        candidates.append(min(config.size_power[f.organization_size], config.legacy_power_cap))
        candidates.append(min(config.net_worth_power[f.net_worth], config.legacy_power_cap))
        if f.highest_office:
            candidates.append(config.office_power)
    return max(candidates)


def _rubric_confidence(
    verdict: JudgeVerdict, dossier: Dossier | None, config: ScoringConfig
) -> float:
    cited = {e for s in verdict.dimension_scores for e in s.evidence_ids}
    if cited and dossier is not None:
        quality = sum(
            config.tier_quality[item.source_tier]
            for item in (dossier.item(e) for e in sorted(cited))
            if item is not None
        )
        return min(1.0, quality / config.evidence_target)
    documented = dossier is not None and bool(dossier.facts.roles)
    return config.documented_zero_confidence if documented else config.undocumented_zero_confidence


def _tier(harm: float, influence: float, final: float, config: ScoringConfig) -> Tier:
    if harm >= config.unwilling_min_harm and influence <= config.unwilling_max_influence:
        return "unwilling"
    if final >= config.tier_ultimate:
        return "ultimate"
    if final >= config.tier_major:
        return "major"
    if final >= config.tier_minor:
        return "minor"
    return "not_a_dick"


def _guardian_tier(score: float, config: ScoringConfig, documented: bool) -> GuardianTier:
    """Tier from the benefit score, with a floor: a benefit the judge scored 1 or higher, with
    cited evidence, is at least Minor, so "none documented" only ever means none was found."""
    if score >= config.benefit_tier_ultimate:
        return "ultimate_guardian"
    if score >= config.benefit_tier_major:
        return "major_guardian"
    if score >= config.benefit_tier_minor or documented:
        return "minor_guardian"
    return "none_documented"


def _combine(terms: Sequence[float], config: ScoringConfig) -> float:
    """Max-dominant: the strongest term, plus the rest with diminishing returns.

    The headroom factor `1 - strongest` means the more extreme the top term, the less the others
    can add, so many small acts never outweigh one major one.
    """
    ordered = sorted(terms, reverse=True)
    if not ordered:
        return 0.0
    strongest = ordered[0]
    rest = min(sum(ordered[1:]), 1.0)
    return strongest + config.combine_rest_weight * (1 - strongest) * rest


def _influence(agency: float, power: float, config: ScoringConfig) -> float:
    return agency * (config.power_floor + (1 - config.power_floor) * power)


def _benefit_influence(
    rubric_id: str,
    score: DimensionScore,
    dossier: Dossier | None,
    role_agency: float,
    role_power: float,
    config: ScoringConfig,
) -> tuple[float, list[str]]:
    """Influence for one benefit dimension, from the acts its score cites.

    Harm uses the person's role. For benefit the question is discretion over this act and the
    scale of what it achieved, so two documented facts can override the role-based values: the
    act went against the role's expectations, or an independently sourced outcome is attributed
    to it.
    """
    cited = [
        item
        for evidence_id in score.evidence_ids
        if dossier is not None and (item := dossier.item(evidence_id)) is not None
    ]
    acts = [(item, item.benefit) for item in cited if item.benefit is not None]
    notes: list[str] = []

    agency = role_agency
    if config.against_role_agency > agency and any(b.against_role for _, b in acts):
        agency = config.against_role_agency
        notes.append(f"{rubric_id} benefit {score.dimension}: acted against role expectations")

    power = role_power
    outcome_powers = [
        config.size_power[b.outcome_scale]
        for item, b in acts
        if b.outcome_attributed
        and b.outcome_scale != "unknown"
        and item.source_tier <= config.outcome_max_source_tier
    ]
    if outcome_powers and max(outcome_powers) > power:
        power = max(outcome_powers)
        notes.append(f"{rubric_id} benefit {score.dimension}: power lifted by documented outcome")

    return _influence(agency, power, config), notes


def _benefit_profile(
    rubrics: Sequence[Rubric],
    verdicts: Mapping[str, JudgeVerdict],
    dossiers: Mapping[str, Dossier],
    role_agency: float,
    role_power: float,
    config: ScoringConfig,
    notes: list[str],
) -> tuple[list[RubricScore], float | None, GuardianTier, float]:
    """The benefit profile: scores, combined score, tier and confidence. Independent of harm."""
    benefit_rubrics = [r for r in rubrics if r.has_benefit]
    scores: list[RubricScore] = []
    terms: list[float] = []
    confidences: list[float] = []
    documented = False
    for rubric in benefit_rubrics:
        verdict = verdicts.get(rubric.id)
        if verdict is None or verdict.insufficient_evidence:
            reason = "no verdict" if verdict is None else "insufficient evidence"
            notes.append(f"{rubric.id} benefit: {reason}")
            scores.append(RubricScore(rubric_id=rubric.id, severity=None))
            continue
        dossier = dossiers.get(rubric.id)
        best_term, top = -1.0, verdict.dimension_scores[0]
        for dim_score in verdict.dimension_scores:
            influence, dim_notes = _benefit_influence(
                rubric.id, dim_score, dossier, role_agency, role_power, config
            )
            notes.extend(dim_notes)
            term = config.severity_strength[dim_score.severity] * influence
            if term > best_term:
                best_term, top = term, dim_score
        terms.append(best_term)
        documented = documented or top.severity >= 1
        confidences.append(_rubric_confidence(verdict, dossier, config))
        scores.append(
            RubricScore(
                rubric_id=rubric.id,
                severity=top.severity,
                top_dimension=top.dimension,
                evidence_ids=top.evidence_ids,
            )
        )

    if not terms:
        return scores, None, "unrated", 0.0
    score = _combine(terms, config)
    coverage = len(terms) / len(benefit_rubrics)
    tier = _guardian_tier(score, config, documented)
    return scores, score, tier, coverage * sum(confidences) / len(terms)


# --- entry point ------------------------------------------------------------


def compute_score(
    verdicts: Sequence[JudgeVerdict],
    dossiers: Sequence[Dossier],
    rubrics: Sequence[Rubric],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> ScoreBreakdown:
    harm_verdicts = {v.rubric_id: v for v in verdicts if v.polarity == "harm"}
    benefit_verdicts = {v.rubric_id: v for v in verdicts if v.polarity == "benefit"}
    dossier_by_id = {d.rubric_id: d for d in dossiers}
    notes: list[str] = []

    rubric_scores: list[RubricScore] = []
    for rubric in rubrics:
        verdict = harm_verdicts.get(rubric.id)
        if not _usable(verdict):
            reason = "no verdict" if verdict is None else "insufficient evidence"
            notes.append(f"{rubric.id}: {reason}")
            rubric_scores.append(RubricScore(rubric_id=rubric.id, severity=None))
            continue
        assert verdict is not None
        top = max(
            verdict.dimension_scores,
            key=lambda s: (
                config.severity_strength[s.severity]
                * config.dimension_weights.get(s.dimension, 1.0)
            ),
        )
        rubric_scores.append(
            RubricScore(
                rubric_id=rubric.id,
                severity=top.severity,
                top_dimension=top.dimension,
                evidence_ids=top.evidence_ids,
            )
        )

    usable_ids = {s.rubric_id for s in rubric_scores if s.severity is not None}
    coverage = len(usable_ids) / len(rubrics) if rubrics else 0.0
    facts = _merge_facts(dossiers)
    agency, roles_known = _agency(facts, config)
    if not roles_known:
        notes.append("no roles documented: agency set to neutral default")
    power = _power(facts, config)
    influence = _influence(agency, power, config)

    benefit_scores, benefit_score, benefit_tier, benefit_confidence = _benefit_profile(
        rubrics, benefit_verdicts, dossier_by_id, agency, power, config, notes
    )
    benefit = {
        "benefit_scores": benefit_scores,
        "benefit_score": benefit_score,
        "benefit_tier": benefit_tier,
        "benefit_confidence": benefit_confidence,
    }

    missing_required = [
        r.id for r in rubrics if r.id in config.required_rubric_ids and r.id not in usable_ids
    ]
    if missing_required:
        notes.append(f"unrated: required rubric(s) without usable evidence: {missing_required}")
        return ScoreBreakdown(
            rubric_scores=rubric_scores,
            power=power,
            agency=agency,
            influence=influence,
            harm_score=None,
            final_score=None,
            tier="unrated",
            coverage=coverage,
            confidence=0.0,
            notes=notes,
            **benefit,
        )

    harm_terms = [
        min(1.0, config.rubric_weights.get(r.id, 1.0) * _strength(harm_verdicts[r.id], config))
        for r in rubrics
        if r.id in usable_ids
    ]
    harm = _combine(harm_terms, config)
    final = harm * influence

    confidences = [
        _rubric_confidence(harm_verdicts[rid], dossier_by_id.get(rid), config)
        for rid in sorted(usable_ids)
    ]
    confidence = coverage * (sum(confidences) / len(confidences))

    return ScoreBreakdown(
        rubric_scores=rubric_scores,
        power=power,
        agency=agency,
        influence=influence,
        harm_score=harm,
        final_score=final,
        tier=_tier(harm, influence, final, config),
        coverage=coverage,
        confidence=confidence,
        notes=notes,
        **benefit,
    )
