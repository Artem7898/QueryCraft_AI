from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pydantic import Field, validator
import secrets
import os


class Settings(BaseSettings):
    # API Keys - БЕЗ значения по умолчанию!
    BYTEZ_API_KEY: str = Field(..., env="BYTEZ_API_KEY")
    MODEL_NAME: str = "Qwen/Qwen2-7B-Instruct"

    # API Settings
    BYTEZ_API_URL: str = Field(
        default="https://api.bytez.com/v1",
        description="Base URL for Bytez API"
    )
    API_TIMEOUT: int = Field(default=30, ge=5, le=120)

    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for signing"
    )
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]

    # Application
    APP_NAME: str = "QueryCraft AI"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="development")

    # Limits
    MAX_QUERY_LENGTH: int = 1000
    MAX_REQUESTS_PER_MINUTE: int = 60

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("DEBUG")
    def validate_debug(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and v:
            raise ValueError("DEBUG cannot be True in production")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()