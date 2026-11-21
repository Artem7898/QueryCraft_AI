"""Query generation and health endpoints."""

from collections.abc import Callable, Coroutine
from time import time
from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.routing import APIRoute
from starlette.types import Message

from app.models.schemas import QueryRequest, QueryResponse
from app.runtime import Runtime, get_runtime

MAX_GENERATION_BODY_BYTES = 16 * 1024


class GenerateRoute(APIRoute):
    """Apply rate and body limits before the request is parsed."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[object, object, Response]]:
        handle = super().get_route_handler()

        async def limited(request: Request) -> Response:
            runtime = await get_runtime(request)
            retry_after = runtime.generation_limit.retry_after()
            if retry_after is not None:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Generation request limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )

            receive = request.receive
            received = 0

            async def limited_receive() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > MAX_GENERATION_BODY_BYTES:
                        raise HTTPException(
                            status.HTTP_413_CONTENT_TOO_LARGE,
                            "Generation request body is too large",
                        )
                return message

            return await handle(Request(request.scope, receive=limited_receive))

        return limited


class HealthStatus(TypedDict):
    """Public API health fields."""

    status: Literal["healthy"]
    model: str
    service: Literal["QueryCraft AI"]
    timestamp: float


router = APIRouter()
generation = APIRouter(route_class=GenerateRoute)


@generation.post(
    "/generate",
    responses={
        413: {"description": "Request body too large"},
        429: {"description": "Generation rate limit exceeded"},
        502: {"description": "Generation provider failed"},
        504: {"description": "Generation provider timed out"},
    },
)
async def generate_query(
    request: QueryRequest,
    runtime: Annotated[Runtime, Depends(get_runtime)],
) -> QueryResponse:
    """Generate query text for review without executing it."""
    if len(request.text) > runtime.max_query_length:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "loc": ["body", "text"],
                    "type": "string_too_long",
                    "msg": f"Description limit is {runtime.max_query_length} characters",
                },
            ],
        )
    return await runtime.service.generate(request)


@router.get("/health")
async def health_check(runtime: Annotated[Runtime, Depends(get_runtime)]) -> HealthStatus:
    """Report process readiness without exposing credential state."""
    return {
        "status": "healthy",
        "model": runtime.service.model,
        "service": "QueryCraft AI",
        "timestamp": time(),
    }


@router.get("/test")
async def test_endpoint() -> dict[str, str | float]:
    """Return the existing connectivity probe through the normal CORS policy."""
    return {
        "message": "✅ CORS тест пройден",
        "timestamp": time(),
        "cors": "enabled",
        "status": "success",
    }


@router.get("/cors-test")
async def cors_test() -> dict[str, str]:
    """Return the existing CORS endpoint response."""
    return {"message": "CORS тест успешен"}


router.include_router(generation)
