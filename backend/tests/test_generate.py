import json
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app


class TrackingTransport(httpx.MockTransport):
    """Observe when the application's HTTP client closes its transport."""

    closed: bool = False

    async def aclose(self) -> None:
        self.closed = True
        await super().aclose()


@pytest.fixture
def provider_settings() -> Settings:
    return Settings(
        BYTEZ_API_KEY=SecretStr("synthetic-test-key"),
        BYTEZ_API_URL="https://provider.example/v1",
        ENVIRONMENT="development",
        DEBUG=False,
        MAX_REQUESTS_PER_MINUTE=60,
        _env_file=None,
    )


def test_offline_generation(client: TestClient, valid_query_request: dict[str, str]) -> None:
    response = client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 200
    data = response.json()
    assert "FROM users" in data["query"]
    assert data["explanation"]
    assert "тестовый режим" in data["model"]
    assert data["executed_in"] >= 0


@pytest.mark.parametrize("db_type", ["postgresql", "mysql", "sqlite", "mongodb"])
@pytest.mark.parametrize("language", ["ru", "en"])
def test_supported_generation_options(client: TestClient, db_type: str, language: str) -> None:
    response = client.post(
        "/api/v1/generate",
        json={
            "text": "Show a sample result",
            "db_type": db_type,
            "complexity": "medium",
            "language": language,
        },
    )

    assert response.status_code == 200
    assert response.json()["query"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": ""},
        {"text": "   "},
        {"text": 123},
        {"text": "Show users", "db_type": "unsupported"},
        {"text": "Show users", "complexity": "unsupported"},
        {"text": "Show users", "language": "unsupported"},
        {"text": "Show users", "unexpected": True},
    ],
)
def test_invalid_requests_are_rejected(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/api/v1/generate", json=payload).status_code == 422


def test_configured_prompt_limit_does_not_echo_text(
    offline_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    settings = offline_settings.model_copy(update={"MAX_QUERY_LENGTH": 10})
    with TestClient(create_app(settings)) as test_client:
        assert (
            test_client.post(
                "/api/v1/generate", json={**valid_query_request, "text": "x" * 10}
            ).status_code
            == 200
        )
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 422
    assert valid_query_request["text"] not in response.text


def test_provider_success_and_transport_lifespan(
    provider_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    observed: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "SELECT id FROM users;\n\nList user IDs."}}],
                "usage": {"total_tokens": 42},
            },
        )

    transport = TrackingTransport(respond)
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        for _ in range(2):
            response = test_client.post("/api/v1/generate", json=valid_query_request)
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "SELECT id FROM users;"
            assert data["explanation"] == "List user IDs."
            assert data["model"] == provider_settings.MODEL_NAME
            assert data["tokens_used"] == 42

        assert len(observed) == 2
        for request in observed:
            assert request.method == "POST"
            assert str(request.url) == "https://provider.example/v1/chat/completions"
            assert request.headers["Authorization"] == "Bearer synthetic-test-key"
            forwarded = json.loads(request.content)
            assert forwarded["model"] == provider_settings.MODEL_NAME
            assert valid_query_request["text"] in forwarded["messages"][-1]["content"]
        assert not transport.closed

    assert transport.closed


@pytest.mark.parametrize(
    ("provider_status", "provider_body"),
    [
        (429, {"detail": "private provider response"}),
        (200, {"choices": []}),
        (200, {"choices": [{"message": {"content": None}}]}),
    ],
)
def test_provider_failure_has_safe_response(
    provider_settings: Settings,
    valid_query_request: dict[str, str],
    provider_status: int,
    provider_body: dict[str, object],
) -> None:
    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(provider_status, json=provider_body)

    transport = httpx.MockTransport(respond)
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 502
    assert response.json()["detail"]
    assert "private provider response" not in response.text
    assert "synthetic-test-key" not in response.text


def test_provider_timeout_has_safe_response(
    provider_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private timeout reason", request=request)

    transport = httpx.MockTransport(fail)
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 504
    assert response.json()["detail"]
    assert "private timeout reason" not in response.text


def test_provider_body_is_bounded_and_closed(
    provider_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    class OversizedBody(httpx.AsyncByteStream):
        closed: bool = False

        async def __aiter__(self) -> AsyncIterator[bytes]:
            for _ in range(17):
                yield b"x" * (16 * 1024)
            raise AssertionError("Provider read continued after exceeding the size limit")

        async def aclose(self) -> None:
            self.closed = True

    body = OversizedBody()
    transport = httpx.MockTransport(lambda _: httpx.Response(200, stream=body))
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 502
    assert body.closed
