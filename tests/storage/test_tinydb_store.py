import asyncio

import pytest

from dont_be_a_dick.domain.schemas import (
    DickScoreReport,
    ScoreBreakdown,
    Subject,
)
from dont_be_a_dick.storage.tinydb_store import TinyDBResultStore

SUBJECT = Subject(name="Test Person", descriptor="CEO")


def make_report() -> DickScoreReport:
    return DickScoreReport(
        subject=SUBJECT,
        tier="minor",
        breakdown=ScoreBreakdown(
            rubric_scores=[],
            power=0.5,
            agency=0.5,
            influence=0.5,
            harm_score=0.3,
            final_score=0.15,
            tier="minor",
            coverage=1,
            confidence=0.7,
        ),
        evidence=[],
        summary="A summary.",
    )


@pytest.fixture
def store() -> TinyDBResultStore:
    return TinyDBResultStore()


async def claim(store: TinyDBResultStore, **kwargs):
    return await store.claim("test-person", SUBJECT, "test", "CEO", **kwargs)


@pytest.mark.anyio
async def test_a_new_id_is_claimed_as_running(store) -> None:
    record, owned = await claim(store)

    assert owned
    assert (record.id, record.status, record.requested_name) == ("test-person", "running", "test")
    assert await store.get("test-person") == record


@pytest.mark.anyio
async def test_unknown_ids_are_none(store) -> None:
    assert await store.get("nobody") is None


@pytest.mark.anyio
async def test_a_running_record_is_returned_not_reclaimed(store) -> None:
    first, _ = await claim(store)

    second, owned = await claim(store)

    assert not owned
    assert second == first


@pytest.mark.anyio
async def test_a_done_record_is_served_until_refreshed(store) -> None:
    await claim(store)
    await store.finish("test-person", make_report())

    cached, owned = await claim(store)
    assert (owned, cached.status, cached.report is not None) == (False, "done", True)

    fresh, owned = await claim(store, refresh=True)
    assert (owned, fresh.status, fresh.report) == (True, "running", None)


@pytest.mark.anyio
async def test_a_failed_record_is_reclaimed(store) -> None:
    await claim(store)
    await store.fail("test-person", "RuntimeError")

    record, owned = await claim(store)

    assert (owned, record.status, record.error) == (True, "running", None)


@pytest.mark.anyio
async def test_concurrent_claims_have_exactly_one_owner(store) -> None:
    results = await asyncio.gather(*(claim(store) for _ in range(10)))

    assert sum(owned for _, owned in results) == 1


@pytest.mark.anyio
async def test_finish_and_fail_update_the_record(store) -> None:
    await claim(store)
    await store.finish("test-person", make_report())
    done = await store.get("test-person")
    assert done.status == "done"
    assert done.report.summary == "A summary."
    assert done.updated_at >= done.created_at

    await claim(store, refresh=True)
    await store.fail("test-person", "RuntimeError")
    failed = await store.get("test-person")
    assert (failed.status, failed.error) == ("failed", "RuntimeError")


@pytest.mark.anyio
async def test_updating_an_unknown_id_raises(store) -> None:
    with pytest.raises(KeyError):
        await store.fail("nobody", "x")


@pytest.mark.anyio
async def test_fail_unfinished_only_touches_running_records(store) -> None:
    await store.claim("a", SUBJECT, "a", None)
    await store.claim("b", SUBJECT, "b", None)
    await store.finish("b", make_report())

    assert await store.fail_unfinished("interrupted") == 1

    assert (await store.get("a")).error == "interrupted"
    assert (await store.get("b")).status == "done"


@pytest.mark.anyio
async def test_records_survive_reopening_the_file(tmp_path) -> None:
    path = tmp_path / "db" / "results.json"
    first = TinyDBResultStore(path)
    await first.claim("test-person", SUBJECT, "test", None)
    await first.finish("test-person", make_report())

    reopened = await TinyDBResultStore(path).get("test-person")

    assert reopened.status == "done"
    assert reopened.report.summary == "A summary."


@pytest.mark.anyio
async def test_each_renewed_run_gets_the_next_run_number(store: TinyDBResultStore) -> None:
    first, _ = await claim(store)
    await store.finish(first.id, make_report())
    again, claimed = await claim(store, refresh=True)

    assert (first.run_number, again.run_number, claimed) == (1, 2, True)
    assert again.session_id == f"{first.id}:2"


@pytest.mark.anyio
async def test_an_unclaimed_request_keeps_its_run_number(store: TinyDBResultStore) -> None:
    first, _ = await claim(store)
    await store.finish(first.id, make_report())
    again, claimed = await claim(store)

    assert (again.run_number, claimed) == (1, False)
