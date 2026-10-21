"""The scoring use case: resolve -> research -> judge -> score -> summarize.

Depends only on the domain ports, so any stage can be faked in tests or swapped
for another implementation (including a LangGraph one). Each step is a method
over an explicit `PipelineState`, so each maps onto a future graph node.
"""

import asyncio
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from dont_be_a_dick.domain.ports import Judge, Researcher, SubjectResolver, Summarizer
from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    Ambiguous,
    DickScoreReport,
    Dossier,
    JudgeVerdict,
    NeedsDisambiguation,
    Refused,
    Resolved,
    ScoreBreakdown,
    Scored,
    ScoreOutcome,
    Subject,
)
from dont_be_a_dick.domain.scoring import DEFAULT_CONFIG, ScoringConfig, compute_score

logger = logging.getLogger(__name__)

SUMMARY_UNAVAILABLE = "Summary unavailable."

ScoreFn = Callable[
    [Sequence[JudgeVerdict], Sequence[Dossier], Sequence[Rubric], ScoringConfig], ScoreBreakdown
]


@dataclass
class PipelineState:
    subject: Subject
    dossiers: dict[str, Dossier] = field(default_factory=dict)
    verdicts: dict[str, JudgeVerdict] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    breakdown: ScoreBreakdown | None = None


class ScoringPipeline:
    def __init__(
        self,
        *,
        resolver: SubjectResolver,
        researcher: Researcher,
        judge: Judge,
        summarizer: Summarizer,
        rubrics: Sequence[Rubric],
        score: ScoreFn = compute_score,
        config: ScoringConfig = DEFAULT_CONFIG,
        max_concurrent_research: int = 3,
    ) -> None:
        self._resolver = resolver
        self._researcher = researcher
        self._judge = judge
        self._summarizer = summarizer
        self._rubrics = list(rubrics)
        self._score = score
        self._config = config
        self._research_slots = asyncio.Semaphore(max_concurrent_research)

    async def run(self, name: str, descriptor: str | None = None) -> ScoreOutcome:
        resolution = await self._resolver.resolve(name, descriptor)
        match resolution:
            case Refused():
                return resolution
            case Ambiguous(candidates=candidates):
                return NeedsDisambiguation(candidates=candidates)
            case Resolved(subject=subject):
                pass

        state = PipelineState(subject=subject)
        await self.gather_dossiers(state)
        await self.judge_dossiers(state)
        self.score(state)
        summary = await self.summarize(state)
        assert state.breakdown is not None
        return Scored(
            report=DickScoreReport(
                subject=subject,
                tier=state.breakdown.tier,
                breakdown=state.breakdown,
                evidence=[item for d in state.dossiers.values() for item in d.items],
                summary=summary,
            )
        )

    async def gather_dossiers(self, state: PipelineState) -> None:
        results = await asyncio.gather(
            *(self._research_limited(state.subject, r) for r in self._rubrics),
            return_exceptions=True,
        )
        for rubric, result in zip(self._rubrics, results, strict=True):
            if isinstance(result, BaseException):
                self._record_failure(state, rubric, "research", result)
            else:
                state.dossiers[rubric.id] = result

    async def _research_limited(self, subject: Subject, rubric: Rubric) -> Dossier:
        """Research agents are the heavy API users, so only a few run at once."""
        async with self._research_slots:
            return await self._researcher.research(subject, rubric)

    async def judge_dossiers(self, state: PipelineState) -> None:
        rubrics = [r for r in self._rubrics if r.id in state.dossiers]
        results = await asyncio.gather(
            *(self._judge.judge(state.dossiers[r.id], r) for r in rubrics),
            return_exceptions=True,
        )
        for rubric, result in zip(rubrics, results, strict=True):
            if isinstance(result, BaseException):
                self._record_failure(state, rubric, "judging", result)
            else:
                state.verdicts[rubric.id] = result

    def score(self, state: PipelineState) -> None:
        breakdown = self._score(
            list(state.verdicts.values()),
            list(state.dossiers.values()),
            self._rubrics,
            self._config,
        )
        failure_notes = [f"{rid}: {why}" for rid, why in state.failures.items()]
        state.breakdown = breakdown.model_copy(update={"notes": [*breakdown.notes, *failure_notes]})

    async def summarize(self, state: PipelineState) -> str:
        assert state.breakdown is not None
        evidence = [item for d in state.dossiers.values() for item in d.items]
        try:
            return await self._summarizer.summarize(state.subject, state.breakdown, evidence)
        except Exception:
            logger.exception("Summarizer failed; returning the score without a summary")
            return SUMMARY_UNAVAILABLE

    @staticmethod
    def _record_failure(
        state: PipelineState, rubric: Rubric, stage: str, error: BaseException
    ) -> None:
        if isinstance(error, asyncio.CancelledError):
            raise error
        logger.error("%s failed for %s: %r", stage, rubric.id, error)
        state.failures[rubric.id] = f"{stage} failed ({type(error).__name__})"
