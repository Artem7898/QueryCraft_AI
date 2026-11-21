"""Process-local resources shared by requests during the ASGI lifespan."""

from dataclasses import dataclass
from math import ceil
from time import monotonic

from fastapi import Request

from app.services.ai_service import AIService


class RateLimiter:
    """Bound generation requests in a fixed, process-local window."""

    def __init__(self, requests_per_minute: int) -> None:
        self._limit = requests_per_minute
        self._count = 0
        self._window_end = 0.0

    def retry_after(self) -> int | None:
        """Consume one slot or return the seconds until the next window."""
        now = monotonic()
        if now >= self._window_end:
            self._count = 0
            self._window_end = now + 60
        if self._count >= self._limit:
            return ceil(self._window_end - now)
        self._count += 1
        return None


@dataclass(frozen=True, slots=True)
class Runtime:
    """Application resources initialized for the serving event loop."""

    service: AIService
    generation_limit: RateLimiter
    max_query_length: int


async def get_runtime(request: Request) -> Runtime:
    """Retrieve the typed state initialized during application startup."""
    runtime = request.state.runtime
    if not isinstance(runtime, Runtime):
        raise RuntimeError("Invalid QueryCraft runtime state")
    return runtime
