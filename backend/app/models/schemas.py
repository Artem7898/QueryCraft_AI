from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


class Complexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    ADVANCED = "advanced"


class QueryRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Описание запроса на естественном языке",
    )
    db_type: DatabaseType = Field(
        default=DatabaseType.POSTGRESQL, description="Тип базы данных"
    )
    complexity: Complexity = Field(
        default=Complexity.MEDIUM, description="Сложность запроса"
    )
    language: str = Field(default="ru", description="Язык запроса (ru/en)")


class QueryResponse(BaseModel):
    query: str = Field(..., description="Сгенерированный SQL/NoSQL запрос")
    explanation: str = Field(..., description="Объяснение запроса")
    executed_in: float = Field(..., description="Время выполнения в секундах")
    tokens_used: Optional[int] = Field(
        None, description="Количество использованных токенов"
    )
    model: str = Field(..., description="Использованная модель")
