"""Stored, asynchronous scoring runs: resolve now, research later, record the result.

`submit` does the quick part (resolve, slug, claim) and says whether the caller now owns a run.
`execute` is the slow part, meant for a background task. `tracked_run` guarantees the stored
record leaves `running` however the run ends.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass

from dont_be_a_dick.domain.ports import ResultStore
from dont_be_a_dick.domain.schemas import (
    DickScoreReport,
    NeedsDisambiguation,
    Refused,
    ResearchRecord,
    Resolved,
)
from dont_be_a_dick.domain.slug import slugify
from dont_be_a_dick.workflows.scoring import ScoringPipeline

logger = logging.getLogger(__name__)

NO_RESULT = "no result"


@dataclass
class Run:
    """Handle yielded by `tracked_run`; set `report` before the block ends to record success."""

    report: DickScoreReport | None = None


@asynccontextmanager
async def tracked_run(store: ResultStore, id: str) -> AsyncIterator[Run]:
    """Move the record out of `running` however the block ends.

    A report on the handle becomes `done`; no report or any exception (cancellation included)
    becomes `failed`. Exceptions are re-raised after being recorded. Only the exception type is
    stored. A hard kill skips this, which is what `ResultStore.fail_unfinished` is for.
    """
    run = Run()
    try:
        yield run
    except BaseException as e:
        # Shielded so a cancellation arriving mid-write cannot leave the record running.
        await asyncio.shield(store.fail(id, type(e).__name__))
        raise
    if run.report is None:
        await store.fail(id, NO_RESULT)
    else:
        await store.finish(id, run.report)


@dataclass(frozen=True)
class Accepted:
    record: ResearchRecord
    claimed: bool
    """True when this call started the run, so the caller must schedule `execute`."""


SubmitOutcome = Accepted | NeedsDisambiguation | Refused


SessionScope = Callable[[str], AbstractContextManager[object]]
"""Opens a scope, keyed by session id, that groups the traces of one run."""


class ResearchService:
    def __init__(
        self,
        pipeline: ScoringPipeline,
        store: ResultStore,
        session_scope: SessionScope = lambda _: nullcontext(),
    ) -> None:
        self._pipeline = pipeline
        self._store = store
        self._session_scope = session_scope

    async def submit(
        self, name: str, descriptor: str | None = None, *, refresh: bool = False
    ) -> SubmitOutcome:
        resolved = await self._pipeline.resolve(name, descriptor)
        if not isinstance(resolved, Resolved):
            return resolved  # ambiguity and refusal are answered, never stored
        subject = resolved.subject
        record, claimed = await self._store.claim(
            slugify(subject.name), subject, name, descriptor, refresh=refresh
        )
        return Accepted(record, claimed)

    async def execute(self, record: ResearchRecord) -> None:
        """Run the pipeline for a record this caller claimed. Never raises except on cancel."""
        try:
            with self._session_scope(record.session_id):
                async with tracked_run(self._store, record.id) as run:
                    scored = await self._pipeline.score_subject(record.subject)
                    run.report = scored.report
        except Exception:
            logger.exception("Scoring run %s failed", record.id)
