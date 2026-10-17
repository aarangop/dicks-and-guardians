import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from tavily import TavilyClient

from dont_be_a_dick import dependencies as deps
from dont_be_a_dick.config import Settings


@pytest.fixture(autouse=True)
def clear_caches():
    deps.get_settings.cache_clear()
    deps.get_tavily_client.cache_clear()
    deps.get_chat_model.cache_clear()
    deps._anthropic_model.cache_clear()
    yield
    deps.get_settings.cache_clear()
    deps.get_tavily_client.cache_clear()
    deps.get_chat_model.cache_clear()
    deps._anthropic_model.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(tavily_api_key="tvly-test", anthropic_api_key="sk-test")


def test_clients_are_singletons_per_settings(settings: Settings) -> None:
    assert deps.get_tavily_client(settings) is deps.get_tavily_client(settings)
    assert deps.get_chat_model(settings) is deps.get_chat_model(settings)


def test_full_chain_builds_an_agent(settings: Settings) -> None:
    tool = deps.get_web_search_tool(deps.get_tavily_client(settings))
    agent = deps.get_research_agent(deps.get_chat_model(settings), tool)

    assert tool.name == "web_search"
    assert hasattr(agent, "invoke")


@pytest.mark.parametrize(
    ("provider", "missing"),
    [
        (deps.get_tavily_client, "DBAD_TAVILY_API_KEY"),
        (deps.get_chat_model, "DBAD_ANTHROPIC_API_KEY"),
    ],
)
def test_missing_keys_give_503(provider, missing: str) -> None:
    with pytest.raises(HTTPException) as exc:
        provider(Settings(tavily_api_key="", anthropic_api_key=""))

    assert exc.value.status_code == 503
    assert missing in exc.value.detail


def test_any_layer_can_be_overridden(settings: Settings) -> None:
    app = FastAPI()

    @app.get("/probe")
    def probe(client: deps.TavilyClientDep) -> dict[str, str]:
        return {"client": type(client).__name__}

    class FakeClient:
        pass

    app.dependency_overrides[deps.get_settings] = lambda: settings
    with TestClient(app) as http:
        assert http.get("/probe").json() == {"client": TavilyClient.__name__}

        app.dependency_overrides[deps.get_tavily_client] = lambda: FakeClient()
        assert http.get("/probe").json() == {"client": "FakeClient"}


def test_agent_dependency_can_be_replaced_wholesale() -> None:
    app = FastAPI()

    @app.get("/probe")
    def probe(agent: deps.ResearchAgentDep) -> dict[str, str]:
        return {"agent": agent}  # type: ignore[dict-item]

    app.dependency_overrides[deps.get_research_agent] = lambda: "fake-agent"

    assert TestClient(app).get("/probe").json() == {"agent": "fake-agent"}


def test_scoring_pipeline_builds_from_settings(settings: Settings) -> None:
    pipeline = deps.build_scoring_pipeline(settings)

    assert type(pipeline).__name__ == "ScoringPipeline"


def test_role_models_are_shared_per_model_name(settings: Settings) -> None:
    # researcher and judge default to the same model, so they share one client
    assert deps.get_researcher_model(settings) is deps.get_judge_model(settings)
    assert deps.get_resolver_model(settings) is not deps.get_judge_model(settings)
