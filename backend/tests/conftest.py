from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def demo_settings() -> Settings:
    """Opt into the deterministic demo workflow for request-contract tests."""
    return Settings(
        BYTEZ_API_KEY=None,
        GENERATION_MODE="demo",
        ENVIRONMENT="development",
        DEBUG=False,
        ALLOWED_ORIGINS=["http://localhost:3000"],
        MAX_REQUESTS_PER_MINUTE=60,
        _env_file=None,
    )


@pytest.fixture
def client(demo_settings: Settings) -> Iterator[TestClient]:
    """Start and stop the ASGI lifespan for each client."""
    with TestClient(create_app(demo_settings)) as test_client:
        yield test_client


@pytest.fixture
def valid_query_request() -> dict[str, str]:
    """Return a request accepted by the public API."""
    return {
        "text": "Show active users",
        "db_type": "postgresql",
        "complexity": "simple",
        "language": "en",
    }
