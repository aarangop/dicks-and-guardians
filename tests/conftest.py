import pytest
from fastapi.testclient import TestClient

from dont_be_a_dick.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
