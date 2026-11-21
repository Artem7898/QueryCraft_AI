"""FastAPI application factory and process lifecycle."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TypedDict

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import query
from app.config import Settings
from app.runtime import RateLimiter, Runtime
from app.services.ai_service import (
    AIService,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class LifespanState(TypedDict):
    """Resources copied into each request's ASGI state."""

    runtime: Runtime


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the API, optionally providing the outbound HTTP transport."""
    config = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[LifespanState]:
        limits = httpx.Limits(
            max_connections=min(20, config.MAX_REQUESTS_PER_MINUTE),
            max_keepalive_connections=min(10, config.MAX_REQUESTS_PER_MINUTE),
        )
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(config.API_TIMEOUT),
            limits=limits,
            transport=transport,
            trust_env=not (config.GENERATION_PROVIDER == "ollama" and config.provider_is_loopback),
        ) as client:
            yield {
                "runtime": Runtime(
                    AIService(config, client),
                    RateLimiter(config.MAX_REQUESTS_PER_MINUTE),
                    config.MAX_QUERY_LENGTH,
                ),
            }

    application = FastAPI(
        title=f"{config.APP_NAME} API",
        description="Генерация текста SQL и NoSQL запросов",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept"],
        max_age=600,
    )
    application.include_router(query.router, prefix="/api/v1", tags=["query"])

    @application.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Only report known locations: unexpected JSON keys can contain user data.
        error_details = []
        for error in exc.errors():
            location = error["loc"]
            if error["type"] == "extra_forbidden":
                location = location[:-1]
            error_details.append(
                {
                    "loc": location,
                    "type": error["type"],
                    "msg": error["msg"],
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": error_details},
        )

    @application.exception_handler(ProviderError)
    async def upstream_error(_: Request, exc: ProviderError) -> JSONResponse:
        if isinstance(exc, ProviderUnavailableError):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Generation provider is not configured"},
            )
        if isinstance(exc, ProviderTimeoutError):
            logger.warning("Query generation provider timed out")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Generation provider timed out"},
            )
        logger.warning("Query generation provider failed")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Generation provider failed"},
        )

    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "message": "QueryCraft AI API",
            "version": "1.0.0",
            "docs": "/api/docs",
            "health": "/api/v1/health",
        }

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "service": "QueryCraft AI"}

    return application


app = create_app()
