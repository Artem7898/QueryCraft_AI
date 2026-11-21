from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


@pytest.fixture
def offline_settings() -> Settings:
    """Configure the built-in offline workflow for tests."""
    return Settings(
        BYTEZ_API_KEY=SecretStr("your_api_key_here"),
        ENVIRONMENT="development",
        DEBUG=False,
        ALLOWED_ORIGINS=["http://localhost:3000"],
        MAX_REQUESTS_PER_MINUTE=60,
        _env_file=None,
    )


@pytest.fixture
def client(offline_settings: Settings) -> Iterator[TestClient]:
    """Start and stop the ASGI lifespan for each client."""
    with TestClient(create_app(offline_settings)) as test_client:
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
