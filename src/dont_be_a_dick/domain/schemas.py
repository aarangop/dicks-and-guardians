"""Data that flows between pipeline stages. All of it is plain, serializable Pydantic."""

from datetime import date, datetime
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


Polarity = Literal["harm", "benefit"]
SizeBand = Literal["unknown", "small", "large", "very_large"]


class BenefitAttrs(BaseModel):
    """What the deterministic layer needs about a benefit act. Extracted, never judged."""

    against_role: bool = Field(
        default=False,
        description=(
            "True when the act went against what the person's role or incentives expected "
            "(a refusal, veto, resignation or disclosure). False for work done as assigned."
        ),
    )
    outcome_scale: SizeBand = Field(
        default="unknown",
        description="Scale of the documented outcome (people or jurisdiction affected)",
    )
    outcome_attributed: bool = Field(
        default=False,
        description="True only when a source itself links the outcome to this act",
    )


class Finding(BaseModel):
    """One sourced fact, as reported by a researcher. The LLM fills this in."""

    claim: str = Field(description="What the person did, stated behaviorally. No character labels.")
    dimension: str = Field(description="Tag of the rubric dimension this fact belongs to")
    polarity: Polarity = Field(
        default="harm",
        description="'harm' for conduct that contributes to the harm; 'benefit' for costly acts "
        "that reduce it",
    )
    benefit: BenefitAttrs | None = Field(
        default=None, description="Only for polarity 'benefit'. Leave empty for harm."
    )
    quote: str = Field(description="Verbatim snippet from the source that supports the claim")
    source_url: str
    source_title: str
    source_kind: SourceKind
    event_date: date | None = Field(default=None, description="When it happened, if known")

    @model_validator(mode="after")
    def _benefit_attrs_only_for_benefit(self) -> "Finding":
        if self.polarity == "harm":
            self.benefit = None
        return self


Seniority = Literal["rank_and_file", "manager", "executive", "founder_or_head_of_state"]
NetWorthBand = Literal["unknown", "under_10m", "10m_to_1b", "1b_to_100b", "over_100b"]
ReachBand = Literal["unknown", "organization", "industry", "national", "global"]
AuthorityKind = Literal["unknown", "none", "shared", "unilateral"]


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
    reach: ReachBand = Field(
        default="unknown",
        description="How far the decisions this person can make or trigger travel: within one "
        "organization, across an industry or region, across a nation, or across many countries",
    )
    authority: AuthorityKind = Field(
        default="unknown",
        description="Can this person bind people who did not consent, through law or force? "
        "'unilateral' by their own decision (head of state or government, an agency head, a "
        "security chief); 'shared' through a vote or seat in a body that binds others "
        "(legislator, judge on a panel); 'none' if they can only persuade, sell or employ",
    )


class ResearchFindings(BaseModel):
    """What a researcher returns. Contains no ids and no tiers: code adds those.

    Every field is required, without a default: a default marks the field optional in the schema
    the model sees, and a model that is short on effort then omits it. An empty list must be
    written out. The searches run are not asked of the model; code reads them from the agent run.
    """

    findings: list[Finding]
    facts: PersonFacts
    gaps: list[str] = Field(
        description="Things the checklist asked for but could not be found; [] if none"
    )


class EvidenceItem(BaseModel):
    id: str
    claim: str
    dimension: str
    polarity: Polarity = "harm"
    benefit: BenefitAttrs | None = None
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

    def with_polarity(self, polarity: Polarity) -> "Dossier":
        """The same dossier restricted to one side, so a judge never sees the other."""
        return self.model_copy(update={"items": [i for i in self.items if i.polarity == polarity]})


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
    polarity: Polarity = "harm"
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
GuardianTier = Literal[
    "ultimate_guardian", "major_guardian", "minor_guardian", "none_documented", "unrated"
]


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
    final_score: float | None = Field(description="harm x influence, None if unrated")
    tier: Tier
    coverage: float = Field(ge=0, le=1, description="Share of rubrics with usable harm evidence")
    confidence: float = Field(ge=0, le=1, description="Computed from evidence tiers and counts")
    benefit_scores: list[RubricScore] = Field(
        default_factory=list, description="Per-rubric benefit severities, kept apart from harm"
    )
    benefit_score: float | None = Field(
        default=None,
        description="0-1 benefit profile (severity x act-level influence), None if unrated. "
        "Never netted against harm.",
    )
    benefit_tier: GuardianTier = "unrated"
    benefit_confidence: float = Field(default=0.0, ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class DickScoreReport(BaseModel):
    subject: Subject
    tier: Tier
    benefit_tier: GuardianTier = "unrated"
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


# --- stored runs ------------------------------------------------------------

RunStatus = Literal["running", "done", "failed"]


class ResearchRecord(BaseModel):
    """One persisted scoring run, keyed by the slug of the subject's canonical name.

    `requested_name` and `descriptor` are what the caller typed, kept so records that ended up
    under different slugs for the same person can be merged later.
    """

    id: str
    run_number: int = Field(
        default=1, ge=1, description="Counts runs of this subject; every renewed run adds one"
    )
    requested_name: str
    descriptor: str | None = None
    subject: Subject
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    report: DickScoreReport | None = None
    error: str | None = Field(default=None, description="Exception type name only, never details")

    @property
    def session_id(self) -> str:
        """Groups everything one run produced, e.g. its traces: `luiz-inacio-lula-da-silva:3`."""
        return f"{self.id}:{self.run_number}"
