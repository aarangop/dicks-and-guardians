import os

# Keep the test suite out of Langfuse. Set before `config` exports `.env`, which never
# overrides variables already in the environment.
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from dont_be_a_dick.main import app


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests that hit real "
        "external APIs (deselect with '-m \"not integration\"')",
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def httpx_mock_fixture(httpx_mock: HTTPXMock) -> HTTPXMock:
    """Fixture to mock external HTTP calls within FastAPI endpoints.

    Use this to mock calls to external APIs (LLM providers, web search, etc.)
    that your FastAPI endpoints make.

    Example:
        httpx_mock_fixture.add_response(
            method="POST",
            url="https://api.openai.com/v1/chat/completions",
            json={"choices": [{"message": {"content": "mocked response"}}]},
        )
    """
    return httpx_mock
