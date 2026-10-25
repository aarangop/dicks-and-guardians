"""TinyDB adapter for the `ResultStore` port.

TinyDB is synchronous and rewrites its whole file on each write, and is not safe across
processes: run a single worker. Every operation takes one lock and runs in a thread, so
`claim`'s check-then-insert is atomic and the event loop is never blocked on disk.
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB
from tinydb.storages import MemoryStorage

from dont_be_a_dick.domain.schemas import DickScoreReport, ResearchRecord, Subject

TABLE = "research"


def _now() -> datetime:
    return datetime.now(UTC)


class TinyDBResultStore:
    def __init__(self, path: Path | None = None) -> None:
        """`path=None` keeps everything in memory (tests)."""
        if path is None:
            self._db = TinyDB(storage=MemoryStorage)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db = TinyDB(path)
        self._table = self._db.table(TABLE)
        self._lock = asyncio.Lock()

    async def _locked[T](self, fn: Callable[[], T]) -> T:
        async with self._lock:
            return await asyncio.to_thread(fn)

    def _load(self, id: str) -> ResearchRecord | None:
        doc = self._table.get(Query().id == id)
        return ResearchRecord.model_validate(doc) if doc else None

    def _save(self, record: ResearchRecord) -> None:
        self._table.upsert(record.model_dump(mode="json"), Query().id == record.id)

    def _update(self, id: str, **fields: Any) -> None:
        record = self._load(id)
        if record is None:
            raise KeyError(id)
        self._save(record.model_copy(update={**fields, "updated_at": _now()}))

    async def claim(
        self,
        id: str,
        subject: Subject,
        requested_name: str,
        descriptor: str | None,
        *,
        refresh: bool = False,
    ) -> tuple[ResearchRecord, bool]:
        def op() -> tuple[ResearchRecord, bool]:
            existing = self._load(id)
            if existing and not refresh and existing.status != "failed":
                return existing, False
            now = _now()
            record = ResearchRecord(
                id=id,
                run_number=existing.run_number + 1 if existing else 1,
                requested_name=requested_name,
                descriptor=descriptor,
                subject=subject,
                status="running",
                created_at=now,
                updated_at=now,
            )
            self._save(record)
            return record, True

        return await self._locked(op)

    async def get(self, id: str) -> ResearchRecord | None:
        return await self._locked(lambda: self._load(id))

    async def finish(self, id: str, report: DickScoreReport) -> None:
        await self._locked(lambda: self._update(id, status="done", report=report, error=None))

    async def fail(self, id: str, error: str) -> None:
        await self._locked(lambda: self._update(id, status="failed", error=error))

    async def fail_unfinished(self, reason: str) -> int:
        def op() -> int:
            stuck = self._table.search(Query().status == "running")
            for doc in stuck:
                self._update(doc["id"], status="failed", error=reason)
            return len(stuck)

        return await self._locked(op)
