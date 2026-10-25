"""Interfaces the pipeline depends on. Adapters (LangChain, Tavily, ...) implement them.

Only domain types cross these boundaries, so any implementation can be swapped
or faked without touching the pipeline.
"""

from collections.abc import Sequence
from typing import Protocol

from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    DickScoreReport,
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    Polarity,
    ResearchRecord,
    Resolution,
    ScoreBreakdown,
    Subject,
)


class SubjectResolver(Protocol):
    async def resolve(self, name: str, descriptor: str | None = None) -> Resolution: ...


class Researcher(Protocol):
    async def research(self, subject: Subject, rubric: Rubric) -> Dossier: ...


class Judge(Protocol):
    async def judge(
        self, dossier: Dossier, rubric: Rubric, polarity: Polarity = "harm"
    ) -> JudgeVerdict:
        """Rate one side of a dossier. The caller passes a dossier already restricted to it."""
        ...


class Summarizer(Protocol):
    async def summarize(
        self, subject: Subject, breakdown: ScoreBreakdown, evidence: Sequence[EvidenceItem]
    ) -> str: ...


class ResultStore(Protocol):
    """Durable record of scoring runs. Every method is safe to call concurrently."""

    async def claim(
        self,
        id: str,
        subject: Subject,
        requested_name: str,
        descriptor: str | None,
        *,
        refresh: bool = False,
    ) -> tuple[ResearchRecord, bool]:
        """Atomically start a run for `id`; returns the record and whether the caller owns it.

        A new or `failed` id (or any id when `refresh`) becomes a fresh `running` record and the
        caller owns it. A `running` or `done` record is returned untouched, not owned.
        Each fresh record carries `run_number`, one more than the record it replaces.
        """
        ...

    async def get(self, id: str) -> ResearchRecord | None: ...

    async def finish(self, id: str, report: DickScoreReport) -> None: ...

    async def fail(self, id: str, error: str) -> None: ...

    async def fail_unfinished(self, reason: str) -> int:
        """Mark every `running` record failed (a crash left them behind); returns how many."""
        ...
