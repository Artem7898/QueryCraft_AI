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
        GENERATION_MODE="live",
        GENERATION_PROVIDER="bytez",
        BYTEZ_API_URL="https://provider.example/v1",
        MODEL_NAME="test-bytez-model",
        ENVIRONMENT="development",
        DEBUG=False,
        MAX_REQUESTS_PER_MINUTE=60,
        _env_file=None,
    )


def reject_unexpected_provider_request(_request: httpx.Request) -> httpx.Response:
    raise AssertionError("This configuration must prevent outbound generation requests")


def test_explicit_demo_generation(
    demo_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    settings = demo_settings.model_copy(update={"BYTEZ_API_KEY": SecretStr("synthetic-test-key")})
    transport = httpx.MockTransport(reject_unexpected_provider_request)
    with TestClient(create_app(settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 200
    data = response.json()
    assert "FROM users" in data["query"]
    assert data["explanation"]
    assert "тестовый режим" in data["model"]
    assert data["source"] == "demo"
    assert data["provider"] is None
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
    assert response.json()["source"] == "demo"


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
        {"text": "Show users", "schema_context": 123},
        {"text": "Show users", "schema_context": "x" * 3001},
    ],
)
def test_invalid_requests_are_rejected(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/api/v1/generate", json=payload).status_code == 422


def test_configured_prompt_limit_does_not_echo_text(
    demo_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    settings = demo_settings.model_copy(update={"MAX_QUERY_LENGTH": 10})
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
        return completion("SELECT id FROM users;\n\nList user IDs.")

    transport = TrackingTransport(respond)
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        for _ in range(2):
            response = test_client.post("/api/v1/generate", json=valid_query_request)
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "SELECT id FROM users;"
            assert data["explanation"] == "List user IDs."
            assert data["model"] == provider_settings.model_name
            assert data["tokens_used"] == 42
            assert data["source"] == "live"
            assert data["provider"] == "bytez"

        assert len(observed) == 2
        for request in observed:
            assert request.method == "POST"
            assert str(request.url) == "https://provider.example/v1/chat/completions"
            assert request.headers["Authorization"] == "Bearer synthetic-test-key"
            forwarded = json.loads(request.content)
            assert forwarded["model"] == provider_settings.model_name
            assert valid_query_request["text"] == forwarded["messages"][-1]["content"]
        assert not transport.closed

    assert transport.closed


def completion(content: str, *, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": content}, "finish_reason": finish_reason}],
            "usage": {"total_tokens": 42},
        },
    )


def test_ollama_completion_extracts_fenced_query_after_prologue(
    provider_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    settings = provider_settings.model_copy(update={"GENERATION_PROVIDER": "ollama"})
    query = "SELECT id\nFROM users\nWHERE active = TRUE;"
    explanation = "Returns the IDs of active users."
    content = (
        "Here is the SQL query for the requested result.\n\n"
        f"```sql\n{query}\n```\n\n"
        f"---\nEXPLANATION---\n{explanation}"
    )
    transport = httpx.MockTransport(lambda _: completion(content))
    with TestClient(create_app(settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "ollama"
    assert data["query"] == query
    assert data["explanation"] == explanation


@pytest.mark.parametrize("provider", ["bytez", "openai"])
def test_live_generation_without_selected_key_is_unavailable(
    provider: str, valid_query_request: dict[str, str]
) -> None:
    settings = Settings(
        BYTEZ_API_KEY=None if provider == "bytez" else SecretStr("synthetic-bytez-key"),
        OPENAI_API_KEY=None if provider == "openai" else SecretStr("synthetic-openai-key"),
        GENERATION_MODE="live",
        GENERATION_PROVIDER=provider,
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    transport = httpx.MockTransport(reject_unexpected_provider_request)
    with TestClient(create_app(settings, transport=transport)) as test_client:
        response = test_client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 503
    assert response.json() == {"detail": "Generation provider is not configured"}


@pytest.mark.parametrize(
    ("provider", "url", "authorization", "model", "token_field"),
    [
        (
            "bytez",
            "https://provider.example/v1/chat/completions",
            "Bearer synthetic-bytez-key",
            "Qwen/Qwen2-7B-Instruct",
            "max_tokens",
        ),
        (
            "openai",
            "https://api.openai.com/v1/chat/completions",
            "Bearer synthetic-openai-key",
            "gpt-4.1-mini",
            "max_completion_tokens",
        ),
        (
            "ollama",
            "http://127.0.0.1:11434/v1/chat/completions",
            None,
            "qwen2.5-coder:1.5b",
            "max_tokens",
        ),
    ],
)
def test_live_providers_route_description_and_schema_context(
    provider: str, url: str, authorization: str | None, model: str, token_field: str
) -> None:
    settings = Settings(
        GENERATION_MODE="live",
        GENERATION_PROVIDER=provider,
        BYTEZ_API_KEY=SecretStr("synthetic-bytez-key"),
        BYTEZ_API_URL="https://provider.example/v1",
        OPENAI_API_KEY=SecretStr("synthetic-openai-key"),
        OLLAMA_API_URL="http://127.0.0.1:11434/v1",
        MODEL_NAME=None,
        ENVIRONMENT="development",
        DEBUG=False,
        MAX_REQUESTS_PER_MINUTE=60,
        _env_file=None,
    )
    schema = "customers(customer_id INTEGER, preferred BOOLEAN, loyalty_points INTEGER)"
    cases = {
        "List preferred customers": (
            "SELECT customer_id FROM customers WHERE preferred IS TRUE;",
            "Filter by preferred status.",
        ),
        "List customers with more than 200 loyalty points": (
            "SELECT customer_id FROM customers WHERE loyalty_points > 200;",
            "Filter by loyalty points.",
        ),
    }
    observed: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == url
        assert request.headers.get("Authorization") == authorization
        payload = json.loads(request.content)
        assert payload["model"] == model
        assert isinstance(payload[token_field], int) and payload[token_field] > 0
        assert {"max_tokens", "max_completion_tokens"} & payload.keys() == {token_field}
        assert "synthetic-bytez-key" not in request.content.decode("utf-8")
        assert "synthetic-openai-key" not in request.content.decode("utf-8")
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        user_message = json.loads(messages[-1]["content"])
        assert user_message["schema_context"] == schema
        description = user_message["text"]
        observed.append(description)
        query, explanation = cases[description]
        return completion(f"{query}\n---EXPLANATION---\n{explanation}")

    transport = httpx.MockTransport(respond)
    with TestClient(create_app(settings, transport=transport)) as test_client:
        for description, (query, explanation) in cases.items():
            response = test_client.post(
                "/api/v1/generate",
                json={
                    "text": description,
                    "db_type": "postgresql",
                    "language": "en",
                    "schema_context": f"  {schema}  ",
                },
            )
            assert response.status_code == 200
            assert response.json()["source"] == "live"
            assert response.json()["provider"] == provider
            assert response.json()["model"] == model
            assert response.json()["query"] == query
            assert response.json()["explanation"] == explanation

    assert observed == list(cases)


@pytest.mark.parametrize(
    ("db_type", "query"),
    [
        (
            "postgresql",
            "SELECT DISTINCT ON (customer_id) customer_id FROM customers ORDER BY customer_id;",
        ),
        ("mysql", "SELECT `name` FROM `customers` WHERE `score` > 10 LIMIT 3;"),
        ("sqlite", "SELECT date(created_at, '-7 days') FROM events WHERE processed = 1;"),
        ("mongodb", "db.orders.find({status: 'open'}).sort({created_at: -1}).limit(3)"),
        ("postgresql", "UPDATE customers SET preferred = TRUE WHERE customer_id = 7;"),
        ("sqlite", "CREATE TABLE purchase_reports (id INTEGER PRIMARY KEY, total NUMERIC);"),
    ],
)
def test_live_generation_accepts_target_dialect(
    provider_settings: Settings, db_type: str, query: str
) -> None:
    transport = httpx.MockTransport(lambda _: completion(query))
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        response = test_client.post(
            "/api/v1/generate",
            json={"text": "Show records meeting the selected condition", "db_type": db_type},
        )

    assert response.status_code == 200
    assert response.json()["query"] == query
    assert response.json()["source"] == "live"


@pytest.mark.parametrize(
    ("db_type", "content", "finish_reason"),
    [
        ("postgresql", "I could not find matching records.", "stop"),
        ("postgresql", "SELECT FROM;", "stop"),
        ("postgresql", "SELECT 1; SELECT 2;", "stop"),
        (
            "postgresql",
            "```sql\nSELECT 1;\n```\n\nAlternatively:\n\n```sql\nSELECT 2;\n```",
            "stop",
        ),
        ("postgresql", "SELECT `id` FROM `customers`;", "stop"),
        ("postgresql", "SELECT id FROM customers;", "length"),
        ("mysql", "SELECT id FROM customers WHERE name ILIKE 'A%';", "stop"),
        ("sqlite", "SELECT id::TEXT FROM customers;", "stop"),
        ("mongodb", "SELECT id FROM customers;", "stop"),
        ("mongodb", "db.customers.find({active: true}", "stop"),
        ("sqlite", "db.customers.find({active: true})", "stop"),
    ],
)
def test_live_generation_rejects_invalid_provider_queries(
    provider_settings: Settings, db_type: str, content: str, finish_reason: str
) -> None:
    transport = httpx.MockTransport(lambda _: completion(content, finish_reason=finish_reason))
    with TestClient(create_app(provider_settings, transport=transport)) as test_client:
        response = test_client.post(
            "/api/v1/generate",
            json={"text": "Show matching customers", "db_type": db_type},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Generation provider failed"}


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
