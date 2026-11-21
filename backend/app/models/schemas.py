"""Request and response contracts for the query generation API."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

QUERY_TEXT_MIN_LENGTH = 3
QUERY_TEXT_MAX_LENGTH = 1000
SCHEMA_CONTEXT_MAX_LENGTH = 3000

type Language = Literal["ru", "en"]
type GenerationSource = Literal["live", "demo"]


class DatabaseType(StrEnum):
    """Database dialects supported by the API."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


class Complexity(StrEnum):
    """Complexity levels the caller can request."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    ADVANCED = "advanced"


class QueryRequest(BaseModel):
    """Describe a query to generate in the chosen database dialect."""

    model_config = ConfigDict(strict=True, extra="forbid")

    text: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=QUERY_TEXT_MIN_LENGTH,
            max_length=QUERY_TEXT_MAX_LENGTH,
        ),
        Field(description="Natural-language query description"),
    ]
    db_type: Annotated[DatabaseType, Field(strict=False, description="Database dialect")] = (
        DatabaseType.POSTGRESQL
    )
    complexity: Annotated[Complexity, Field(strict=False, description="Query complexity")] = (
        Complexity.MEDIUM
    )
    language: Annotated[Language, Field(description="Request language")] = "ru"
    schema_context: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, max_length=SCHEMA_CONTEXT_MAX_LENGTH),
            Field(description="Relevant tables, collections, columns, or relationships"),
        ]
        | None
    ) = None

    @field_validator("text")
    @classmethod
    def reject_null_character(cls, text: str) -> str:
        """Reject embedded NUL characters in the request description."""
        if "\x00" in text:
            raise ValueError("Query text must not contain a NUL character")
        return text

    @field_validator("schema_context")
    @classmethod
    def normalize_schema_context(cls, context: str | None) -> str | None:
        """Treat blank schema context as absent and reject embedded NUL characters."""
        if context is not None and "\x00" in context:
            raise ValueError("Schema context must not contain a NUL character")
        return context or None


class QueryResponse(BaseModel):
    """Generated query with provider metadata and an explanation."""

    model_config = ConfigDict(strict=True)

    query: Annotated[str, Field(min_length=1, description="Generated SQL or NoSQL")]
    explanation: Annotated[str, Field(description="Query explanation")]
    executed_in: Annotated[
        float, Field(ge=0, allow_inf_nan=False, description="Elapsed time in seconds")
    ]
    tokens_used: Annotated[int, Field(ge=0, description="Number of tokens used")] | None = None
    model: Annotated[str, Field(min_length=1, description="Model used")]
    source: Annotated[GenerationSource, Field(description="Origin of the generated query")]
