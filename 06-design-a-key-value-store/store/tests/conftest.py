import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())
