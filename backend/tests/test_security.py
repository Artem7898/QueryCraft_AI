import json
import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.query import MAX_GENERATION_BODY_BYTES
from app.config import Settings
from app.main import create_app


def test_cors_preflight_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/generate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_preflight_rejects_unconfigured_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/generate",
        headers={
            "Origin": "https://unconfigured.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_bare_options_has_no_cors_wildcard(client: TestClient) -> None:
    response = client.options("/api/v1/generate")

    assert "access-control-allow-origin" not in response.headers


def test_rate_limit_is_atomic_and_resets_with_lifespan(
    demo_settings: Settings, valid_query_request: dict[str, str]
) -> None:
    settings = demo_settings.model_copy(update={"MAX_REQUESTS_PER_MINUTE": 2})
    app = create_app(settings)

    with TestClient(app) as test_client, ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(
                lambda _: test_client.post("/api/v1/generate", json=valid_query_request),
                range(4),
            )
        )
        assert sorted(response.status_code for response in responses) == [200, 200, 429, 429]
        for response in responses:
            if response.status_code == 429:
                assert 1 <= int(response.headers["retry-after"]) <= 60
        assert test_client.get("/api/v1/health").status_code == 200

    with TestClient(app) as restarted:
        assert restarted.post("/api/v1/generate", json=valid_query_request).status_code == 200


def test_oversized_body_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/generate", json={"text": "x" * MAX_GENERATION_BODY_BYTES})

    assert response.status_code == 413


def test_oversized_streamed_body_is_rejected(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"text":"'
        yield b"x" * (MAX_GENERATION_BODY_BYTES // 2)
        yield b"x" * (MAX_GENERATION_BODY_BYTES // 2)
        yield b'"}'

    response = client.post(
        "/api/v1/generate",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert "content-length" not in response.request.headers
    assert response.status_code == 413


def test_byte_limit_allows_full_unicode_prompt_and_schema(client: TestClient) -> None:
    payload = {"text": "🌿" * 1000, "schema_context": "🌿" * 3000}
    response = client.post(
        "/api/v1/generate",
        content=json.dumps(payload, ensure_ascii=True),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["source"] == "demo"


def test_validation_and_logs_omit_request_content_and_headers(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    private_prompt = "private prompt test marker"
    private_header = "private header test marker"
    caplog.set_level(logging.INFO)

    response = client.post(
        "/api/v1/generate",
        json={"text": {"note": private_prompt}},
        headers={"Authorization": private_header},
    )

    assert response.status_code == 422
    assert private_prompt not in response.text
    assert private_prompt not in caplog.text
    assert private_header not in caplog.text
    assert any(error["loc"][-1] == "text" for error in response.json()["detail"])
