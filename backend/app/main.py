from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.endpoints import query
from app.services.ai_service import ai_service
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    # Startup
    logger.info("Starting QueryCraft AI API...")

    if not settings.BYTEZ_API_KEY:
        logger.error("BYTEZ_API_KEY is not set!")
        raise ValueError("BYTEZ_API_KEY не установлен")

    logger.info(f"Using model: {settings.MODEL_NAME}")
    logger.info("API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down QueryCraft AI API...")
    await ai_service.close()


app = FastAPI(
    title="QueryCraft AI API",
    description="API для генерации SQL-запросов с помощью AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware - ВАЖНО: добавить ДО всех маршрутов
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Allow-Headers",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["Content-Disposition"],
    max_age=600,  # 10 минут кэширования preflight запросов
)


# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")

    response = await call_next(request)

    logger.info(f"Response status: {response.status_code}")
    return response


# Подключаем роутеры
app.include_router(query.router, prefix="/api/v1", tags=["query"])


@app.get("/")
async def root():
    return {
        "message": "QueryCraft AI API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "QueryCraft AI"}


# Явно обрабатываем OPTIONS запросы для всех маршрутов
#@app.options("/api/v1/{path:path}")
#async def options_handler(path: str):
#    return {"message": "CORS preflight OK"}
