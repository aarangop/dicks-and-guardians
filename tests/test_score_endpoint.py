import pytest
from fastapi.testclient import TestClient

from dont_be_a_dick.config import Settings
from dont_be_a_dick.dependencies import get_scoring_pipeline
from dont_be_a_dick.domain.schemas import (
    DickScoreReport,
    NeedsDisambiguation,
    Refused,
    ScoreBreakdown,
    Scored,
    Subject,
)
from dont_be_a_dick.main import app


def report() -> DickScoreReport:
    return DickScoreReport(
        subject=Subject(name="Test Person"),
        tier="minor",
        breakdown=ScoreBreakdown(
            rubric_scores=[],
            power=0.5,
            agency=0.5,
            influence=0.5,
            harm_score=0.3,
            counterweight_reduction=0,
            final_score=0.15,
            tier="minor",
            coverage=1,
            confidence=0.7,
        ),
        evidence=[],
        summary="A summary.",
    )


class FakePipeline:
    def __init__(self, outcome=None, error: Exception | None = None) -> None:
        self.outcome = outcome
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    async def run(self, name: str, descriptor: str | None = None):
        self.calls.append((name, descriptor))
        if self.error:
            raise self.error
        return self.outcome


@pytest.fixture
def use_pipeline():
    def _use(pipeline: FakePipeline) -> None:
        app.dependency_overrides[get_scoring_pipeline] = lambda: pipeline

    yield _use
    app.dependency_overrides.clear()


def test_score_returns_the_report(client: TestClient, use_pipeline) -> None:
    pipeline = FakePipeline(Scored(report=report()))
    use_pipeline(pipeline)

    response = client.post("/score", json={"name": " Test Person ", "descriptor": "CEO"})

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "minor"
    assert body["summary"] == "A summary."
    assert body["breakdown"]["final_score"] == 0.15
    assert pipeline.calls == [("Test Person", "CEO")]


def test_ambiguous_names_return_409_with_candidates(client: TestClient, use_pipeline) -> None:
    candidates = [Subject(name="P", descriptor="a"), Subject(name="P", descriptor="b")]
    use_pipeline(FakePipeline(NeedsDisambiguation(candidates=candidates)))

    response = client.post("/score", json={"name": "P"})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert [c["descriptor"] for c in detail["candidates"]] == ["a", "b"]


def test_refused_subjects_return_422_with_the_reason(client: TestClient, use_pipeline) -> None:
    use_pipeline(FakePipeline(Refused(reason="private individual")))

    response = client.post("/score", json={"name": "Nobody"})

    assert response.status_code == 422
    assert response.json()["detail"] == "private individual"


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "   "}])
def test_invalid_names_are_rejected_before_the_pipeline(
    client: TestClient, use_pipeline, body: dict
) -> None:
    pipeline = FakePipeline(Scored(report=report()))
    use_pipeline(pipeline)

    response = client.post("/score", json=body)

    assert response.status_code == 422
    assert pipeline.calls == []


def test_pipeline_failures_are_a_502_without_leaking_details(
    client: TestClient, use_pipeline
) -> None:
    use_pipeline(FakePipeline(error=RuntimeError("anthropic key sk-secret")))

    response = client.post("/score", json={"name": "Someone"})

    assert response.status_code == 502
    assert "sk-secret" not in response.text


def test_missing_keys_give_503_through_the_real_dependency_chain(client: TestClient) -> None:
    from dont_be_a_dick import dependencies as deps

    deps.get_settings.cache_clear()
    deps._anthropic_model.cache_clear()
    deps.get_tavily_client.cache_clear()
    app.dependency_overrides[deps.get_settings] = lambda: Settings(
        tavily_api_key="", anthropic_api_key=""
    )
    try:
        response = client.post("/score", json={"name": "Someone"})
    finally:
        app.dependency_overrides.clear()
        deps.get_settings.cache_clear()

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
