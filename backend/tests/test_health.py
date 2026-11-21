from fastapi.testclient import TestClient

from app.config import Settings


def test_api_health_endpoint(client: TestClient, demo_settings: Settings) -> None:
    response = client.get("/api/v1/health?detailed=true")

    assert response.status_code == 200
    health = response.json()
    assert set(health) == {"status", "model", "service", "timestamp"}
    assert health["status"] == "healthy"
    assert health["model"] == demo_settings.MODEL_NAME
    assert health["service"] == "QueryCraft AI"
    assert isinstance(health["timestamp"], int | float)
