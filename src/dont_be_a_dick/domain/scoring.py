"""Deterministic scoring: judge verdicts + extracted facts in, `ScoreBreakdown` out.

Pure functions, no I/O, no LLM. The same inputs always give the same output
(rubric principle 2). Every number lives in `ScoringConfig`, so calibration
means changing config, not code. The defaults are a first guess to be tuned.

How it works:
1. Per rubric, severity per dimension -> strength in 0-1 (`severity_strength`),
   take the max over dimensions so one catastrophic act is not diluted.
2. Harm rubrics combine with a weighted probabilistic OR (never an average).
3. Harm is multiplied by influence (agency x power), so rank and file rank lower.
4. Counterweight rubrics can only reduce the result, up to `counterweight_cap`.
5. Missing required rubrics give `unrated`. Coverage and confidence are computed
   from what was usable, not self-reported by judges.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import prod

from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    DimensionScore,
    Dossier,
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
    office_power: float = 0.8
    power_floor: float = 0.4
    """Even a powerless person keeps this share of the influence multiplier."""

    counterweight_cap: float = 0.3

    tier_ultimate: float = 0.75
    tier_major: float = 0.45
    tier_minor: float = 0.1
    unwilling_min_harm: float = 0.4
    unwilling_max_influence: float = 0.3

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
    candidates = [config.size_power["unknown"], config.net_worth_power["unknown"]]
    for f in facts:
        candidates.append(config.size_power[f.organization_size])
        candidates.append(config.net_worth_power[f.net_worth])
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


# --- entry point ------------------------------------------------------------


def compute_score(
    verdicts: Sequence[JudgeVerdict],
    dossiers: Sequence[Dossier],
    rubrics: Sequence[Rubric],
    config: ScoringConfig = DEFAULT_CONFIG,
) -> ScoreBreakdown:
    verdict_by_id = {v.rubric_id: v for v in verdicts}
    dossier_by_id = {d.rubric_id: d for d in dossiers}
    notes: list[str] = []

    rubric_scores: list[RubricScore] = []
    for rubric in rubrics:
        verdict = verdict_by_id.get(rubric.id)
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
    influence = agency * (config.power_floor + (1 - config.power_floor) * power)

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
            counterweight_reduction=0.0,
            final_score=None,
            tier="unrated",
            coverage=coverage,
            confidence=0.0,
            notes=notes,
        )

    harm_terms = [
        config.rubric_weights.get(r.id, 1.0) * _strength(verdict_by_id[r.id], config)
        for r in rubrics
        if r.kind == "harm" and r.id in usable_ids
    ]
    harm = 1 - prod(1 - term for term in harm_terms)

    counter_strengths = [
        _strength(verdict_by_id[r.id], config)
        for r in rubrics
        if r.kind == "counterweight" and r.id in usable_ids
    ]
    reduction = config.counterweight_cap * max(counter_strengths, default=0.0)

    final = harm * influence * (1 - reduction)

    confidences = [
        _rubric_confidence(verdict_by_id[rid], dossier_by_id.get(rid), config)
        for rid in sorted(usable_ids)
    ]
    confidence = coverage * (sum(confidences) / len(confidences))

    return ScoreBreakdown(
        rubric_scores=rubric_scores,
        power=power,
        agency=agency,
        influence=influence,
        harm_score=harm,
        counterweight_reduction=reduction,
        final_score=final,
        tier=_tier(harm, influence, final, config),
        coverage=coverage,
        confidence=confidence,
        notes=notes,
    )
