import pytest
from pydantic import ValidationError


def test_query_request_validation():
    """Тест валидации модели запроса."""
    from app.api.v1.endpoints.query import QueryRequest

    # Валидные данные
    valid_data = {
        "text": "Найти активных пользователей",
        "db_type": "postgresql",
        "complexity": "simple",
        "language": "ru",
    }

    request = QueryRequest(**valid_data)
    assert request.text == valid_data["text"]
    assert request.db_type == valid_data["db_type"]
    assert request.complexity == valid_data["complexity"]
    assert request.language == valid_data["language"]

    # Невалидные данные
    invalid_data = {
        "text": "",  # Пустой текст
        "db_type": "invalid_db",  # Неподдерживаемый тип БД
        "complexity": "invalid",
        "language": "fr",  # Неподдерживаемый язык
    }

    with pytest.raises(ValidationError):
        QueryRequest(**invalid_data)


def test_query_response_model():
    """Тест модели ответа."""
    from app.api.v1.endpoints.query import QueryResponse

    response_data = {
        "query": "SELECT * FROM users;",
        "explanation": "Select all users",
        "model": "gpt-3.5-turbo",
        "executed_in": 1.5,
    }

    response = QueryResponse(**response_data)
    assert response.query == response_data["query"]
    assert response.explanation == response_data["explanation"]
    assert response.model == response_data["model"]
    assert response.executed_in == response_data["executed_in"]
