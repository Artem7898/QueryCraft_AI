import pytest
from pydantic import ValidationError

from app.models.schemas import Complexity, DatabaseType, QueryRequest, QueryResponse


def test_query_request_normalizes_text_and_preserves_defaults() -> None:
    request = QueryRequest(text="  Show users  ")

    assert request.text == "Show users"
    assert request.db_type is DatabaseType.POSTGRESQL
    assert request.complexity is Complexity.MEDIUM
    assert request.language == "ru"
    assert request.schema_context is None


@pytest.mark.parametrize("length", [3, 1000])
def test_query_request_inclusive_length_limits(length: int) -> None:
    assert len(QueryRequest(text=" " + "x" * length + " ").text) == length


@pytest.mark.parametrize("text", ["  xx  ", "x" * 1001, "sample\0text"])
def test_query_request_rejects_invalid_text(text: str) -> None:
    with pytest.raises(ValidationError):
        QueryRequest(text=text)


def test_query_request_schema_context_is_optional_and_trimmed() -> None:
    assert QueryRequest(text="Show users", schema_context="   ").schema_context is None
    assert QueryRequest(text="Show users", schema_context="\n users(id) \n").schema_context == (
        "users(id)"
    )
    context = "x" * 3000
    assert QueryRequest(text="Show users", schema_context=f" {context} ").schema_context == context


def test_query_request_rejects_embedded_null_in_schema_context() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(text="Show users", schema_context="users\0(id)")


def test_query_response_preserves_wire_types() -> None:
    response = QueryResponse(
        query="SELECT id FROM users;",
        explanation="List user IDs.",
        model="test-model",
        executed_in=1.5,
        source="live",
    )

    assert response.model_dump(mode="json") == {
        "query": "SELECT id FROM users;",
        "explanation": "List user IDs.",
        "model": "test-model",
        "executed_in": 1.5,
        "tokens_used": None,
        "source": "live",
    }


@pytest.mark.parametrize(
    ("executed_in", "tokens_used"),
    [(float("inf"), 1), (float("nan"), 0), (-1.0, 0), (0.0, -1)],
)
def test_query_response_rejects_invalid_metrics(executed_in: float, tokens_used: int) -> None:
    with pytest.raises(ValidationError):
        QueryResponse(
            query="SELECT 1;",
            explanation="Return a constant.",
            model="test-model",
            executed_in=executed_in,
            tokens_used=tokens_used,
            source="live",
        )
