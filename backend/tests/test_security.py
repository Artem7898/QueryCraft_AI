import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.security import sanitize_input, SQLInjectionError

client = TestClient(app)


def test_sql_injection_prevention():
    """Тест защиты от SQL инъекций"""
    malicious_inputs = [
        "SELECT * FROM users; DROP TABLE users; --",
        "' OR '1'='1",
        "admin' --",
        "1; DELETE FROM users",
        "UNION SELECT * FROM passwords",
    ]

    for malicious in malicious_inputs:
        with pytest.raises((ValueError, SQLInjectionError)):
            sanitize_input(malicious)


def test_cors_headers():
    """Тест CORS заголовков"""
    response = client.options("/api/v1/generate")
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers


def test_rate_limiting():
    """Тест ограничения запросов"""
    responses = []
    for _ in range(10):
        response = client.post("/api/v1/generate", json={
            "text": "test",
            "db_type": "postgresql",
            "complexity": "simple"
        })
        responses.append(response.status_code)

    # Проверяем, что не все запросы прошли (если rate limiting включен)
    assert any(r != 200 for r in responses), "Rate limiting not working"


def test_api_key_not_logged():
    """Тест, что API ключ не логируется"""
    response = client.get("/api/v1/health")
    assert "api_key" not in response.text.lower()
    assert "B72c830aee09a35f763208e26c948eef" not in response.text