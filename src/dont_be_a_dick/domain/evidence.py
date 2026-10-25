"""Turning researcher output into a dossier, and checking judge verdicts against it.

Pure functions: ids and source tiers are assigned here, in code, never by an LLM.
"""

from collections.abc import Sequence
from urllib.parse import urlparse

from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    Polarity,
    ResearchFindings,
    SourceKind,
    SourceTier,
    Subject,
)

_TIER_BY_KIND: dict[SourceKind, SourceTier] = {
    "court_record": 1,
    "regulatory_filing": 1,
    "primary_document": 1,
    "investigative_journalism": 2,
    "news_report": 2,
    "opinion_or_advocacy": 3,
    "other": 3,
}
_PRIMARY_SOURCE_SUFFIXES = (".gov", ".mil", ".europa.eu")
_PRIMARY_SOURCE_HOSTS = ("courtlistener.com",)


def classify_tier(kind: SourceKind, url: str) -> SourceTier:
    """Tier from the declared kind, upgraded to 1 for known primary-source hosts.

    Opinion and advocacy never upgrade: a .gov blog post is still opinion.
    """
    tier = _TIER_BY_KIND[kind]
    if kind == "opinion_or_advocacy":
        return tier
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(_PRIMARY_SOURCE_SUFFIXES) or host in _PRIMARY_SOURCE_HOSTS:
        return 1
    return tier


def build_dossier(
    subject: Subject,
    rubric: Rubric,
    research: ResearchFindings,
    queries_run: Sequence[str] = (),
) -> Dossier:
    """Assign ids and tiers, drop duplicates and findings outside the rubric's dimensions.

    Benefit findings are kept only for rubrics that have benefit anchors.
    """
    items: list[EvidenceItem] = []
    seen: set[tuple[str, str]] = set()
    dropped_unknown = 0
    dropped_benefit = 0
    for finding in research.findings:
        if finding.dimension not in rubric.tags:
            dropped_unknown += 1
            continue
        if finding.polarity == "benefit" and not rubric.has_benefit:
            dropped_benefit += 1
            continue
        key = (finding.source_url, finding.claim)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            EvidenceItem(
                id=f"{rubric.id}-E{len(items) + 1:02d}",
                source_tier=classify_tier(finding.source_kind, finding.source_url),
                **finding.model_dump(),
            )
        )
    gaps = list(research.gaps)
    if dropped_unknown:
        gaps.append(f"dropped {dropped_unknown} finding(s) tagged with an unknown dimension")
    if dropped_benefit:
        gaps.append(
            f"dropped {dropped_benefit} benefit finding(s): {rubric.id} has no benefit side"
        )
    return Dossier(
        rubric_id=rubric.id,
        subject=subject,
        items=items,
        facts=research.facts,
        queries_run=list(queries_run),
        gaps=gaps,
    )


def check_verdict(
    verdict: JudgeVerdict, dossier: Dossier, rubric: Rubric, polarity: Polarity = "harm"
) -> list[str]:
    """Problems that need the dossier to detect. Empty list means the verdict is sound."""
    problems: list[str] = []
    if verdict.rubric_id != rubric.id:
        problems.append(f"verdict is for {verdict.rubric_id!r}, expected {rubric.id!r}")
    if verdict.polarity != polarity:
        problems.append(f"verdict polarity is {verdict.polarity!r}, expected {polarity!r}")
    for score in verdict.dimension_scores:
        if score.dimension not in rubric.tags:
            problems.append(f"unknown dimension {score.dimension!r}; valid: {list(rubric.tags)}")
        cited = []
        for evidence_id in score.evidence_ids:
            item = dossier.item(evidence_id)
            if item is None:
                problems.append(f"{score.dimension}: cites unknown evidence id {evidence_id!r}")
            else:
                cited.append(item)
        if score.severity >= 1 and cited and all(i.source_tier == 3 for i in cited):
            problems.append(
                f"{score.dimension}: severity {score.severity} rests only on tier-3 sources"
            )
    return problems


class VerdictError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems
