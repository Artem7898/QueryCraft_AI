def test_health_endpoint(client):
    """Тест эндпоинта проверки здоровья."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"  # Изменено с "ok" на "healthy"


def test_health_endpoint_with_details(client):
    """Тест эндпоинта здоровья с проверкой деталей."""
    response = client.get("/api/v1/health?detailed=true")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "service" in data
    assert (
        data["service"] == "QueryCraft AI"
    )  # Изменено с "QueryCraft AI API" на "QueryCraft AI"
