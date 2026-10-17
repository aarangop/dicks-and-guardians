"""Data that flows between pipeline stages. All of it is plain, serializable Pydantic."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# --- subject ----------------------------------------------------------------


class Subject(BaseModel, frozen=True):
    """The person being scored. `descriptor` disambiguates common names."""

    name: str = Field(min_length=1)
    descriptor: str | None = Field(
        default=None, description="Short disambiguator, e.g. 'Australian moral philosopher'"
    )


class Resolved(BaseModel):
    kind: Literal["resolved"] = "resolved"
    subject: Subject


class Ambiguous(BaseModel):
    kind: Literal["ambiguous"] = "ambiguous"
    candidates: list[Subject] = Field(min_length=2)


class Refused(BaseModel):
    """Not a notable public figure, or otherwise out of scope."""

    kind: Literal["refused"] = "refused"
    reason: str


Resolution = Annotated[Resolved | Ambiguous | Refused, Field(discriminator="kind")]


# --- research ---------------------------------------------------------------

SourceKind = Literal[
    "court_record",
    "regulatory_filing",
    "primary_document",
    "investigative_journalism",
    "news_report",
    "opinion_or_advocacy",
    "other",
]
SourceTier = Literal[1, 2, 3]


class Finding(BaseModel):
    """One sourced fact, as reported by a researcher. The LLM fills this in."""

    claim: str = Field(description="What the person did, stated behaviorally. No character labels.")
    dimension: str = Field(description="Tag of the rubric dimension this fact belongs to")
    quote: str = Field(description="Verbatim snippet from the source that supports the claim")
    source_url: str
    source_title: str
    source_kind: SourceKind
    event_date: date | None = Field(default=None, description="When it happened, if known")


Seniority = Literal["rank_and_file", "manager", "executive", "founder_or_head_of_state"]
SizeBand = Literal["unknown", "small", "large", "very_large"]
NetWorthBand = Literal["unknown", "under_10m", "10m_to_1b", "1b_to_100b", "over_100b"]


class Role(BaseModel):
    title: str
    organization: str
    seniority: Seniority
    start_year: int | None = None
    end_year: int | None = Field(default=None, description="None means current")
    voluntary: bool | None = Field(default=None, description="None means unknown")


class PersonFacts(BaseModel):
    """Structured facts the deterministic layer needs. Extracted, never judged."""

    roles: list[Role] = Field(default_factory=list)
    highest_office: str | None = None
    organization_size: SizeBand = "unknown"
    net_worth: NetWorthBand = "unknown"


class ResearchFindings(BaseModel):
    """What a researcher returns. Contains no ids and no tiers: code adds those."""

    findings: list[Finding] = Field(default_factory=list)
    facts: PersonFacts = Field(default_factory=PersonFacts)
    queries_run: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(
        default_factory=list, description="Things the checklist asked for but could not be found"
    )


class EvidenceItem(BaseModel):
    id: str
    claim: str
    dimension: str
    quote: str
    source_url: str
    source_title: str
    source_kind: SourceKind
    source_tier: SourceTier
    event_date: date | None = None


class Dossier(BaseModel):
    rubric_id: str
    subject: Subject
    items: list[EvidenceItem] = Field(default_factory=list)
    facts: PersonFacts = Field(default_factory=PersonFacts)
    queries_run: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)

    def item(self, evidence_id: str) -> EvidenceItem | None:
        return next((i for i in self.items if i.id == evidence_id), None)


# --- judging ----------------------------------------------------------------

Severity = Literal[0, 1, 2, 3, 4]


class DimensionScore(BaseModel):
    dimension: str
    severity: Severity
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(
        min_length=1, description="Why this level and not the next one up, citing the anchor"
    )

    @model_validator(mode="after")
    def _severity_needs_evidence(self) -> "DimensionScore":
        if self.severity >= 1 and not self.evidence_ids:
            raise ValueError(f"severity {self.severity} for {self.dimension!r} cites no evidence")
        return self


class JudgeVerdict(BaseModel):
    """A judge's rating of one dossier against one rubric. No self-reported confidence."""

    rubric_id: str
    insufficient_evidence: bool = Field(
        description="True when the dossier cannot support any rating. Then give no scores."
    )
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    rationale: str = Field(min_length=1, description="Overall reasoning, short")

    @model_validator(mode="after")
    def _consistent(self) -> "JudgeVerdict":
        if self.insufficient_evidence and self.dimension_scores:
            raise ValueError("insufficient_evidence verdicts must not include scores")
        if not self.insufficient_evidence and not self.dimension_scores:
            raise ValueError(
                "a verdict needs at least one dimension score or insufficient_evidence"
            )
        dims = [s.dimension for s in self.dimension_scores]
        if len(dims) != len(set(dims)):
            raise ValueError("each dimension may be scored at most once")
        return self


# --- scoring ----------------------------------------------------------------

Tier = Literal["ultimate", "major", "unwilling", "minor", "not_a_dick", "unrated"]


class RubricScore(BaseModel):
    rubric_id: str
    severity: int | None = Field(description="Max severity across dimensions, None if unrated")
    top_dimension: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    rubric_scores: list[RubricScore]
    power: float = Field(ge=0, le=1)
    agency: float = Field(ge=0, le=1)
    influence: float = Field(ge=0, le=1, description="Multiplier derived from agency and power")
    harm_score: float | None = Field(description="0-1 combined raw harm, None if unrated")
    counterweight_reduction: float = Field(ge=0, le=1)
    final_score: float | None = Field(
        description="harm x influence x (1 - counterweight), None if unrated"
    )
    tier: Tier
    coverage: float = Field(ge=0, le=1, description="Share of rubrics with usable evidence")
    confidence: float = Field(ge=0, le=1, description="Computed from evidence tiers and counts")
    notes: list[str] = Field(default_factory=list)


class DickScoreReport(BaseModel):
    subject: Subject
    tier: Tier
    breakdown: ScoreBreakdown
    evidence: list[EvidenceItem]
    summary: str


# --- pipeline outcome -------------------------------------------------------


class Scored(BaseModel):
    kind: Literal["scored"] = "scored"
    report: DickScoreReport


class NeedsDisambiguation(BaseModel):
    kind: Literal["needs_disambiguation"] = "needs_disambiguation"
    candidates: list[Subject]


ScoreOutcome = Annotated[Scored | NeedsDisambiguation | Refused, Field(discriminator="kind")]
