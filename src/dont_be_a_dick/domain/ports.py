"""Interfaces the pipeline depends on. Adapters (LangChain, Tavily, ...) implement them.

Only domain types cross these boundaries, so any implementation can be swapped
or faked without touching the pipeline.
"""

from collections.abc import Sequence
from typing import Protocol

from dont_be_a_dick.domain.rubrics import Rubric
from dont_be_a_dick.domain.schemas import (
    Dossier,
    EvidenceItem,
    JudgeVerdict,
    Resolution,
    ScoreBreakdown,
    Subject,
)


class SubjectResolver(Protocol):
    async def resolve(self, name: str, descriptor: str | None = None) -> Resolution: ...


class Researcher(Protocol):
    async def research(self, subject: Subject, rubric: Rubric) -> Dossier: ...


class Judge(Protocol):
    async def judge(self, dossier: Dossier, rubric: Rubric) -> JudgeVerdict: ...


class Summarizer(Protocol):
    async def summarize(
        self, subject: Subject, breakdown: ScoreBreakdown, evidence: Sequence[EvidenceItem]
    ) -> str: ...
