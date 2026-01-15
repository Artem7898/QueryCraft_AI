import pytest
from fastapi.testclient import TestClient

def test_root_endpoint(client: TestClient):
    """Тест корневого эндпоинта"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "QueryCraft AI API"

def test_health_endpoint(client: TestClient):
    """Тест health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_cors_preflight(client: TestClient):
    """Тест CORS preflight"""
    response = client.options(
        "/api/v1/generate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        }
    )
    # OPTIONS должен возвращать 200
    assert response.status_code == 200