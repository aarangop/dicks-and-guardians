from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from dont_be_a_dick.config import Settings
from dont_be_a_dick.dependencies import get_research_agent
from dont_be_a_dick.main import app


class FakeAgent:
    def __init__(self, reply: AIMessage | Exception) -> None:
        self.reply = reply
        self.inputs: list[dict[str, Any]] = []

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.inputs.append(inputs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return {"messages": [self.reply]}


@pytest.fixture
def use_agent():
    def _use(agent: FakeAgent) -> None:
        app.dependency_overrides[get_research_agent] = lambda: agent

    yield _use
    app.dependency_overrides.clear()


def test_research_returns_final_answer_as_plain_text(client: TestClient, use_agent) -> None:
    agent = FakeAgent(AIMessage(content="Peter Singer is a philosopher."))
    use_agent(agent)

    response = client.post("/research", json={"name": "Peter Singer"})

    assert response.status_code == 200
    assert response.json() == {
        "name": "Peter Singer",
        "summary": "Peter Singer is a philosopher.",
    }
    [call] = agent.inputs
    assert "Peter Singer" in call["messages"][0]["content"]


def test_research_joins_text_blocks(client: TestClient, use_agent) -> None:
    blocks = [{"type": "text", "text": "Part one. "}, {"type": "text", "text": "Part two."}]
    use_agent(FakeAgent(AIMessage(content=blocks)))

    response = client.post("/research", json={"name": "Someone"})

    assert response.json()["summary"] == "Part one. Part two."


def test_research_strips_the_name(client: TestClient, use_agent) -> None:
    use_agent(FakeAgent(AIMessage(content="ok")))

    response = client.post("/research", json={"name": "  Peter Singer "})

    assert response.json()["name"] == "Peter Singer"


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "   "}, {"nombre": "x"}])
def test_research_rejects_invalid_names(client: TestClient, use_agent, body: dict) -> None:
    agent = FakeAgent(AIMessage(content="unused"))
    use_agent(agent)

    response = client.post("/research", json=body)

    assert response.status_code == 422
    assert agent.inputs == []


def test_research_agent_failure_is_a_502(client: TestClient, use_agent) -> None:
    use_agent(FakeAgent(RuntimeError("anthropic is down")))

    response = client.post("/research", json={"name": "Someone"})

    assert response.status_code == 502
    assert "anthropic is down" not in response.text


@pytest.mark.integration
def test_research_with_real_services(client: TestClient) -> None:
    settings = Settings()
    if not (
        settings.anthropic_api_key.get_secret_value() and settings.tavily_api_key.get_secret_value()
    ):
        pytest.skip("DBAD_ANTHROPIC_API_KEY and DBAD_TAVILY_API_KEY must be set")

    response = client.post("/research", json={"name": "Peter Singer"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Peter Singer"
    assert len(body["summary"]) > 300
    assert "singer" in body["summary"].lower()
