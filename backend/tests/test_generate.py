import pytest


def test_generate_without_auth(client):
    """Тест генерации без авторизации."""
    response = client.post(
        "/api/v1/generate",
        json={
            "text": "test query",
            "db_type": "postgresql",
            "complexity": "simple",
            "language": "ru",
        },
    )

    # Должен вернуть 200 даже без API ключа (если используется мок)
    assert response.status_code in [200, 401]


def test_generate_with_missing_fields(client):
    """Тест генерации с пропущенными обязательными полями."""
    response = client.post("/api/v1/generate", json={})

    assert response.status_code == 422  # Validation error


def test_generate_with_empty_text(client):
    """Тест генерации с пустым текстом."""
    response = client.post(
        "/api/v1/generate",
        json={
            "text": "",
            "db_type": "postgresql",
            "complexity": "simple",
            "language": "ru",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_with_mock_ai(client, mocker, valid_query_request):
    """Тест генерации с моком AI API."""
    # Мокаем запрос к внешнему AI API
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "SELECT * FROM users WHERE active = true; -- Active users"
                }
            }
        ]
    }

    # Убираем with и используем просто патч
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    response = client.post("/api/v1/generate", json=valid_query_request)

    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "explanation" in data
    assert "model" in data
    assert "executed_in" in data


def test_generate_with_different_db_types(client, mocker):
    """Тест генерации для разных типов БД."""
    db_types = ["postgresql", "mysql", "sqlite", "mongodb"]

    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test query"}}]
    }

    # Убираем with
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    for db_type in db_types:
        response = client.post(
            "/api/v1/generate",
            json={
                "text": "test",
                "db_type": db_type,
                "complexity": "simple",
                "language": "ru",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "query" in data


def test_generate_with_different_languages(client, mocker):
    """Тест генерации на разных языках."""
    languages = ["ru", "en"]

    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test query"}}]
    }

    # Убираем with
    mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    for language in languages:
        response = client.post(
            "/api/v1/generate",
            json={
                "text": "test query",
                "db_type": "postgresql",
                "complexity": "simple",
                "language": language,
            },
        )

        assert response.status_code == 200
