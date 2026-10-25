import asyncio
from contextlib import contextmanager

import pytest

from dont_be_a_dick.domain.schemas import (
    NeedsDisambiguation,
    Refused,
    Resolved,
    Scored,
    Subject,
)
from dont_be_a_dick.storage.tinydb_store import TinyDBResultStore
from dont_be_a_dick.workflows.research_runs import (
    NO_RESULT,
    Accepted,
    ResearchService,
    tracked_run,
)
from tests.storage.test_tinydb_store import make_report

LULA = Subject(name="Luiz Inácio Lula da Silva", descriptor="Brazilian president")


class FakePipeline:
    def __init__(self, resolution=None, error: BaseException | None = None) -> None:
        self.resolution = resolution or Resolved(subject=LULA)
        self.error = error
        self.resolved: list[tuple[str, str | None]] = []
        self.scored: list[Subject] = []

    async def resolve(self, name, descriptor=None):
        self.resolved.append((name, descriptor))
        return self.resolution

    async def score_subject(self, subject):
        self.scored.append(subject)
        if self.error:
            raise self.error
        return Scored(report=make_report())


@pytest.fixture
def store() -> TinyDBResultStore:
    return TinyDBResultStore()


def service(pipeline: FakePipeline, store) -> ResearchService:
    return ResearchService(pipeline, store)  # type: ignore[arg-type]


# --- tracked_run -------------------------------------------------------------


async def claimed(store, id: str = "x") -> str:
    await store.claim(id, LULA, "lula", None)
    return id


@pytest.mark.anyio
async def test_tracked_run_records_done_when_a_report_is_set(store) -> None:
    id = await claimed(store)

    async with tracked_run(store, id) as run:
        run.report = make_report()

    assert (await store.get(id)).status == "done"


@pytest.mark.anyio
async def test_tracked_run_fails_a_block_that_set_no_report(store) -> None:
    id = await claimed(store)

    async with tracked_run(store, id):
        pass

    record = await store.get(id)
    assert (record.status, record.error) == ("failed", NO_RESULT)


@pytest.mark.anyio
async def test_tracked_run_records_failure_and_reraises(store) -> None:
    id = await claimed(store)

    with pytest.raises(RuntimeError):
        async with tracked_run(store, id):
            raise RuntimeError("secret detail")

    record = await store.get(id)
    assert (record.status, record.error) == ("failed", "RuntimeError")


@pytest.mark.anyio
async def test_tracked_run_records_cancellation_and_propagates_it(store) -> None:
    id = await claimed(store)
    started = asyncio.Event()

    async def work() -> None:
        async with tracked_run(store, id):
            started.set()
            await asyncio.sleep(10)

    task = asyncio.create_task(work())
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    record = await store.get(id)
    assert (record.status, record.error) == ("failed", "CancelledError")


# --- ResearchService ---------------------------------------------------------


@pytest.mark.anyio
async def test_submit_claims_under_the_slug_of_the_canonical_name(store) -> None:
    outcome = await service(FakePipeline(), store).submit("Lula", "president")

    assert isinstance(outcome, Accepted)
    assert outcome.claimed
    record = outcome.record
    assert (record.id, record.status) == ("luiz-inacio-lula-da-silva", "running")
    assert (record.requested_name, record.descriptor) == ("Lula", "president")
    assert record.subject == LULA


@pytest.mark.anyio
async def test_submit_stores_nothing_for_ambiguity_or_refusal(store) -> None:
    candidates = [Subject(name="P", descriptor="a"), Subject(name="P", descriptor="b")]
    ambiguous = await service(
        FakePipeline(NeedsDisambiguation(candidates=candidates)), store
    ).submit("P")
    refused = await service(FakePipeline(Refused(reason="private")), store).submit("P")

    assert isinstance(ambiguous, NeedsDisambiguation)
    assert refused == Refused(reason="private")
    assert await store.fail_unfinished("x") == 0
    assert await store.get("p") is None


@pytest.mark.anyio
async def test_a_second_submit_does_not_claim_again(store) -> None:
    svc = service(FakePipeline(), store)
    first = await svc.submit("Lula")
    second = await svc.submit("Lula da Silva")

    assert first.claimed and not second.claimed
    assert second.record.id == first.record.id


@pytest.mark.anyio
async def test_execute_stores_the_report(store) -> None:
    pipeline = FakePipeline()
    svc = service(pipeline, store)
    outcome = await svc.submit("Lula")

    await svc.execute(outcome.record)

    record = await store.get(outcome.record.id)
    assert record.status == "done"
    assert record.report.summary == "A summary."
    assert pipeline.scored == [LULA]


@pytest.mark.anyio
async def test_execute_records_a_pipeline_error_without_raising(store) -> None:
    svc = service(FakePipeline(error=RuntimeError("anthropic key sk-secret")), store)
    outcome = await svc.submit("Lula")

    await svc.execute(outcome.record)

    record = await store.get(outcome.record.id)
    assert (record.status, record.error) == ("failed", "RuntimeError")
    assert "sk-secret" not in record.model_dump_json()


@pytest.mark.anyio
async def test_execute_lets_cancellation_through(store) -> None:
    svc = service(FakePipeline(error=asyncio.CancelledError()), store)
    outcome = await svc.submit("Lula")

    with pytest.raises(asyncio.CancelledError):
        await svc.execute(outcome.record)

    assert (await store.get(outcome.record.id)).status == "failed"


@pytest.mark.anyio
async def test_execute_runs_inside_the_session_of_its_run(store) -> None:
    events: list[str] = []

    @contextmanager
    def scope(session_id: str):
        events.append(f"open {session_id}")
        yield
        events.append("close")

    pipeline = FakePipeline()
    svc = ResearchService(pipeline, store, session_scope=scope)  # type: ignore[arg-type]
    first = (await svc.submit("lula")).record
    await svc.execute(first)
    second = (await svc.submit("lula", refresh=True)).record
    await svc.execute(second)

    assert events == [f"open {first.id}:1", "close", f"open {first.id}:2", "close"]
