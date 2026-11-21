"""Generate SQL or MongoDB queries without connecting to a database."""

import asyncio
import json
import re
from collections.abc import Callable
from time import perf_counter
from typing import NotRequired, TypedDict, TypeGuard

import httpx

from app.config import Settings
from app.models.schemas import DatabaseType, Language, QueryRequest, QueryResponse

_MAX_RESPONSE_BYTES = 256 * 1024
_EXPLANATION_MARKER = "---EXPLANATION---"
_EXPLANATION_LINE = re.compile(rf"^[ \t]*{_EXPLANATION_MARKER}[ \t]*$", re.MULTILINE)
_FENCED_QUERY = re.compile(
    r"\A```[^\n]*\n(?P<query>.*?)\n```[ \t]*(?:\n|$)(?P<explanation>.*)\Z",
    re.DOTALL,
)


class ProviderError(Exception):
    """The upstream generation service could not complete a request."""


class ProviderTimeoutError(ProviderError):
    """The upstream generation deadline expired."""


class ProviderResponseError(ProviderError):
    """The upstream response does not match the expected completion format."""


class _CompletionMessage(TypedDict):
    content: str


class _CompletionChoice(TypedDict):
    message: _CompletionMessage


class _CompletionUsage(TypedDict):
    total_tokens: int


class _CompletionPayload(TypedDict):
    choices: list[_CompletionChoice]
    usage: NotRequired[_CompletionUsage | None]


def _is_choice(value: object) -> TypeGuard[_CompletionChoice]:
    if not isinstance(value, dict):
        return False
    message = value.get("message")
    if not isinstance(message, dict):
        return False
    content = message.get("content")
    return isinstance(content, str) and bool(content.strip())


def _is_completion(value: object) -> TypeGuard[_CompletionPayload]:
    if not isinstance(value, dict):
        return False
    choices = value.get("choices")
    if not isinstance(choices, list) or not choices or not all(map(_is_choice, choices)):
        return False

    usage = value.get("usage")
    if usage is None:
        return True
    if not isinstance(usage, dict):
        return False
    total_tokens = usage.get("total_tokens")
    return (
        isinstance(total_tokens, int) and not isinstance(total_tokens, bool) and total_tokens >= 0
    )


class AIService:
    """Generate a query using Bytez or a deterministic offline example.

    The application owns the injected HTTP client and its connection pool.
    """

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    @property
    def model(self) -> str:
        """Return the model identifier advertised by the service."""
        return self._settings.MODEL_NAME

    async def generate(self, request: QueryRequest) -> QueryResponse:
        """Generate query text and an explanation for a validated request.

        Raises:
            ProviderError: Bytez could not produce a valid completion.
            ProviderTimeoutError: Bytez exceeded the configured deadline.
        """
        started_at = perf_counter()
        key = self._settings.BYTEZ_API_KEY
        if self._settings.offline or key is None:
            return _offline_response(request, self.model, started_at)

        payload: dict[str, object] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _system_prompt(request)},
                {"role": "user", "content": request.text},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
            "top_p": 0.95,
        }
        completion = await self._post_json(payload, key.get_secret_value(), _is_completion)
        query, explanation = _parse_completion(
            completion["choices"][0]["message"]["content"], request.language
        )
        usage = completion.get("usage")
        return QueryResponse(
            query=query,
            explanation=explanation,
            executed_in=round(perf_counter() - started_at, 2),
            tokens_used=usage["total_tokens"] if usage is not None else 0,
            model=self.model,
        )

    async def _post_json[T](
        self,
        payload: dict[str, object],
        token: str,
        is_valid: Callable[[object], TypeGuard[T]],
    ) -> T:
        body = bytearray()
        try:
            async with (
                asyncio.timeout(self._settings.API_TIMEOUT),
                self._client.stream(
                    "POST",
                    f"{self._settings.BYTEZ_API_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    },
                    json=payload,
                    follow_redirects=False,
                ) as response,
            ):
                response.raise_for_status()
                if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                    raise ProviderResponseError("Bytez returned an unsupported content encoding")
                async for chunk in response.aiter_bytes(chunk_size=16 * 1024):
                    if len(body) + len(chunk) > _MAX_RESPONSE_BYTES:
                        raise ProviderResponseError("Bytez response exceeds the size limit")
                    body.extend(chunk)
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise ProviderTimeoutError("Bytez response deadline exceeded") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("Bytez request failed") from exc

        try:
            decoded: object = json.loads(body)
        except (ValueError, RecursionError) as exc:
            raise ProviderResponseError("Bytez returned invalid JSON") from exc
        if not is_valid(decoded):
            raise ProviderResponseError("Bytez returned an invalid completion")
        return decoded


def _system_prompt(request: QueryRequest) -> str:
    dialect = "MongoDB Shell" if request.db_type is DatabaseType.MONGODB else request.db_type.value
    if request.language == "ru":
        return (
            f"Сгенерируй запрос для {dialect} уровня {request.complexity.value}. "
            "Используй диалект указанной базы данных. Сначала верни только текст запроса. "
            f"Затем помести {_EXPLANATION_MARKER} на отдельной строке "
            "и кратко объясни запрос на русском."
        )
    return (
        f"Generate a {request.complexity.value} query for {dialect}. "
        "Use the selected database dialect. Return the query first. "
        f"Then put {_EXPLANATION_MARKER} on its own line "
        "and briefly explain the query in English."
    )


def _parse_completion(content: str, language: Language) -> tuple[str, str]:
    """Extract query text, preserving internal blank lines."""
    text = content.strip().replace("\r\n", "\n")
    if text.startswith("```"):
        match = _FENCED_QUERY.fullmatch(text)
        if match is None:
            raise ProviderResponseError("Bytez returned an incomplete query block")
        query = match["query"]
        explanation = match["explanation"].lstrip().removeprefix(_EXPLANATION_MARKER)
    else:
        marker = _EXPLANATION_LINE.search(text)
        if marker is not None:
            query, explanation = text[: marker.start()], text[marker.end() :]
        else:
            # The older protocol separated explanations with a blank line.
            # A statement terminator makes that split unambiguous for typical output.
            query, blank, explanation = text.rpartition("\n\n")
            if not blank or not query.rstrip().endswith(";"):
                query, explanation = text, ""

    query = query.strip()
    if not query:
        raise ProviderResponseError("Bytez returned an empty query")
    fallback = "Сгенерированный запрос" if language == "ru" else "Generated query"
    return query, explanation.strip() or fallback


_ORDER_CUTOFF = {
    DatabaseType.POSTGRESQL: "CURRENT_DATE - INTERVAL '30 days'",
    DatabaseType.MYSQL: "CURRENT_DATE - INTERVAL 30 DAY",
    DatabaseType.SQLITE: "date('now', '-30 days')",
}


def _offline_response(request: QueryRequest, model: str, started_at: float) -> QueryResponse:
    text = request.text.casefold()
    if "users" in text or "пользовател" in text:
        query = (
            'db.users.find({ status: "active", age: { $gt: 25 } })'
            ".sort({ created_at: -1 }).limit(100)"
            if request.db_type is DatabaseType.MONGODB
            else (
                "SELECT id, username, email, age, status, created_at\n"
                "FROM users\n"
                "WHERE status = 'active' AND age > 25\n"
                "ORDER BY created_at DESC\n"
                "LIMIT 100;"
            )
        )
        explanation = (
            "Выбирает активных пользователей старше 25 лет"
            if request.language == "ru"
            else "Selects active users older than 25"
        )
    elif "orders" in text or "заказ" in text:
        if request.db_type is DatabaseType.MONGODB:
            query = (
                "db.orders.aggregate([\n"
                '  { $match: { $expr: { $gte: ["$created_at", { $dateSubtract: {\n'
                '    startDate: "$$NOW", unit: "day", amount: 30\n'
                "  } }] } } },\n"
                '  { $group: { _id: { $dateTrunc: { date: "$created_at", unit: "day" } },\n'
                '    total_orders: { $sum: 1 }, total_amount: { $sum: "$amount" },\n'
                '    average_order: { $avg: "$amount" } } },\n'
                "  { $sort: { _id: -1 } }\n"
                "])"
            )
        else:
            cutoff = _ORDER_CUTOFF[request.db_type]
            query = (
                "SELECT DATE(created_at) AS order_date, COUNT(*) AS total_orders,\n"
                "       SUM(amount) AS total_amount, AVG(amount) AS average_order\n"
                "FROM orders\n"
                f"WHERE created_at >= {cutoff}\n"
                "GROUP BY DATE(created_at)\n"
                "ORDER BY order_date DESC;"
            )
        explanation = (
            "Статистика заказов за последние 30 дней"
            if request.language == "ru"
            else "Summarizes orders over the last 30 days"
        )
    else:
        query = (
            'db.example_table.find({ condition: "value" }).sort({ _id: 1 }).limit(50)'
            if request.db_type is DatabaseType.MONGODB
            else "SELECT *\nFROM example_table\nWHERE condition = 'value'\nORDER BY id\nLIMIT 50;"
        )
        explanation = (
            f"Пример запроса для {request.db_type.value}"
            if request.language == "ru"
            else f"Example query for {request.db_type.value}"
        )

    return QueryResponse(
        query=query,
        explanation=explanation,
        executed_in=round(perf_counter() - started_at, 2),
        tokens_used=150,
        model=f"{model} (тестовый режим)",
    )
