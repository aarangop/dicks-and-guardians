import asyncio

import pytest
from fastapi.testclient import TestClient

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.config import Settings
from dont_be_a_dick.domain.schemas import NeedsDisambiguation, Refused, Resolved, Scored, Subject
from dont_be_a_dick.main import app
from dont_be_a_dick.storage.tinydb_store import TinyDBResultStore
from dont_be_a_dick.workflows.research_runs import ResearchService
from tests.storage.test_tinydb_store import make_report

LULA = Subject(name="Luiz Inácio Lula da Silva", descriptor="Brazilian president")


class FakePipeline:
    def __init__(
        self,
        resolution=None,
        resolve_error: Exception | None = None,
        score_error: Exception | None = None,
    ) -> None:
        self.resolution = resolution or Resolved(subject=LULA)
        self.resolve_error = resolve_error
        self.score_error = score_error
        self.resolved: list[tuple[str, str | None]] = []
        self.scored: list[Subject] = []

    async def resolve(self, name: str, descriptor: str | None = None):
        self.resolved.append((name, descriptor))
        if self.resolve_error:
            raise self.resolve_error
        return self.resolution

    async def score_subject(self, subject: Subject) -> Scored:
        self.scored.append(subject)
        if self.score_error:
            raise self.score_error
        return Scored(report=make_report())


@pytest.fixture
def store() -> TinyDBResultStore:
    return TinyDBResultStore()


@pytest.fixture
def use_pipeline(store):
    def _use(pipeline: FakePipeline) -> None:
        app.dependency_overrides[deps.get_research_service] = lambda: ResearchService(
            pipeline,  # type: ignore[arg-type]
            store,
        )
        app.dependency_overrides[deps.get_result_store] = lambda: store

    yield _use
    app.dependency_overrides.clear()


def test_score_accepts_the_request_and_the_result_can_be_polled(
    client: TestClient, use_pipeline
) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)

    response = client.post("/score", json={"name": " Lula ", "descriptor": "president"})

    assert response.status_code == 202
    assert response.json() == {"id": "luiz-inacio-lula-da-silva", "status": "running"}
    assert response.headers["location"] == "/score/luiz-inacio-lula-da-silva"
    assert pipeline.resolved == [("Lula", "president")]

    # TestClient runs background tasks before returning, so the run has finished by now.
    polled = client.get(response.headers["location"])
    assert polled.status_code == 200
    body = polled.json()
    assert (body["status"], body["requested_name"]) == ("done", "Lula")
    assert body["report"]["summary"] == "A summary."
    assert body["error"] is None


def test_a_repeated_request_serves_the_stored_result_without_rerunning(
    client: TestClient, use_pipeline
) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)
    client.post("/score", json={"name": "Lula"})

    again = client.post("/score", json={"name": "Lula da Silva"})

    assert again.status_code == 202
    assert again.json() == {"id": "luiz-inacio-lula-da-silva", "status": "done"}
    assert len(pipeline.scored) == 1


def test_refresh_reruns_a_finished_subject(client: TestClient, use_pipeline) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)
    client.post("/score", json={"name": "Lula"})

    client.post("/score?refresh=true", json={"name": "Lula"})

    assert len(pipeline.scored) == 2


def test_a_failed_run_is_polled_as_failed_and_retried_on_resubmit(
    client: TestClient, use_pipeline
) -> None:
    use_pipeline(FakePipeline(score_error=RuntimeError("anthropic key sk-secret")))

    client.post("/score", json={"name": "Lula"})
    polled = client.get("/score/luiz-inacio-lula-da-silva")

    assert polled.json()["status"] == "failed"
    assert polled.json()["error"] == "RuntimeError"
    assert "sk-secret" not in polled.text

    pipeline = FakePipeline()
    use_pipeline(pipeline)
    client.post("/score", json={"name": "Lula"})
    assert client.get("/score/luiz-inacio-lula-da-silva").json()["status"] == "done"


def test_a_running_subject_is_joined_not_restarted(client: TestClient, use_pipeline, store) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)
    asyncio.run(store.claim("luiz-inacio-lula-da-silva", LULA, "x", None))

    response = client.post("/score", json={"name": "Lula"})

    assert response.json() == {"id": "luiz-inacio-lula-da-silva", "status": "running"}
    assert pipeline.scored == []


def test_unknown_ids_are_404(client: TestClient, use_pipeline) -> None:
    use_pipeline(FakePipeline())

    assert client.get("/score/nobody").status_code == 404


def test_ambiguous_names_return_409_with_candidates_and_store_nothing(
    client: TestClient, use_pipeline, store
) -> None:
    candidates = [Subject(name="P", descriptor="a"), Subject(name="P", descriptor="b")]
    use_pipeline(FakePipeline(NeedsDisambiguation(candidates=candidates)))

    response = client.post("/score", json={"name": "P"})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert [c["descriptor"] for c in detail["candidates"]] == ["a", "b"]
    assert client.get("/score/p").status_code == 404


def test_refused_subjects_return_422_with_the_reason(client: TestClient, use_pipeline) -> None:
    use_pipeline(FakePipeline(Refused(reason="private individual")))

    response = client.post("/score", json={"name": "Nobody"})

    assert response.status_code == 422
    assert response.json()["detail"] == "private individual"


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "   "}])
def test_invalid_names_are_rejected_before_the_pipeline(
    client: TestClient, use_pipeline, body: dict
) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)

    response = client.post("/score", json=body)

    assert response.status_code == 422
    assert pipeline.resolved == []


def test_resolution_failures_are_a_502_without_leaking_details(
    client: TestClient, use_pipeline
) -> None:
    use_pipeline(FakePipeline(resolve_error=RuntimeError("anthropic key sk-secret")))

    response = client.post("/score", json={"name": "Someone"})

    assert response.status_code == 502
    assert "sk-secret" not in response.text


def test_startup_marks_interrupted_runs_as_failed(use_pipeline, store) -> None:
    use_pipeline(FakePipeline())
    asyncio.run(store.claim("stuck", LULA, "x", None))

    with TestClient(app):
        pass

    record = asyncio.run(store.get("stuck"))
    assert (record.status, record.error) == ("failed", "interrupted by restart")


def test_missing_keys_give_503_through_the_real_dependency_chain(client: TestClient, store) -> None:
    deps.get_settings.cache_clear()
    deps._openrouter_model.cache_clear()
    deps.get_tavily_client.cache_clear()
    app.dependency_overrides[deps.get_result_store] = lambda: store
    app.dependency_overrides[deps.get_settings] = lambda: Settings(
        tavily_api_key="", openrouter_api_key=""
    )
    try:
        response = client.post("/score", json={"name": "Someone"})
    finally:
        app.dependency_overrides.clear()
        deps.get_settings.cache_clear()

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


@pytest.mark.parametrize("descriptor", ["", "   ", None])
def test_a_blank_descriptor_is_treated_as_none(
    client: TestClient, use_pipeline, descriptor: str | None
) -> None:
    pipeline = FakePipeline()
    use_pipeline(pipeline)

    client.post("/score", json={"name": "Lula", "descriptor": descriptor})

    assert pipeline.resolved == [("Lula", None)]
