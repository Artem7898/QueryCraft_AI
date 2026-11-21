"""Load and validate application settings from the environment."""

import json
from typing import Annotated, Self
from urllib.parse import SplitResult, urlsplit

from pydantic import (
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.models.schemas import QUERY_TEXT_MAX_LENGTH, QUERY_TEXT_MIN_LENGTH

OFFLINE_BYTEZ_KEY = "your_api_key_here"


def _parse_http_url(value: str, schemes: tuple[str, ...]) -> SplitResult:
    """Validate a configured HTTP URL without leaking it in error messages."""
    if any(character.isspace() for character in value):
        raise ValueError("URL must not contain whitespace")

    try:
        url = urlsplit(value)
        # urllib validates port syntax when the parsed port is accessed.
        _ = url.port
    except ValueError:
        raise ValueError("Invalid HTTP URL") from None
    if (
        url.scheme not in schemes
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or "?" in value
        or "#" in value
        or "\\" in value
    ):
        raise ValueError(
            "URL must have an allowed scheme and host, without credentials, "
            "query parameters or a fragment"
        )
    return url


class Settings(BaseSettings):
    """Settings bound to an application instance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    BYTEZ_API_KEY: SecretStr | None = None
    MODEL_NAME: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = (
        "Qwen/Qwen2-7B-Instruct"
    )
    BYTEZ_API_URL: str = "https://api.bytez.com/models/v2/openai/v1"
    API_TIMEOUT: Annotated[int, Field(ge=5, le=120)] = 30
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://0.0.0.0:8000",
        ],
    )
    APP_NAME: str = "QueryCraft AI"
    DEBUG: bool = False
    ENVIRONMENT: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = (
        "development"
    )
    MAX_QUERY_LENGTH: Annotated[int, Field(ge=QUERY_TEXT_MIN_LENGTH, le=QUERY_TEXT_MAX_LENGTH)] = (
        QUERY_TEXT_MAX_LENGTH
    )
    MAX_REQUESTS_PER_MINUTE: Annotated[int, Field(gt=0)] = 60

    @property
    def offline(self) -> bool:
        """Return whether generation uses local examples."""
        key = self.BYTEZ_API_KEY
        if key is None:
            return True
        return key.get_secret_value() == OFFLINE_BYTEZ_KEY

    @field_validator("BYTEZ_API_KEY")
    @classmethod
    def validate_provider_key(cls, key: SecretStr | None) -> SecretStr | None:
        """Normalize an optional API key and ensure it can be sent in a header."""
        if key is None:
            return None
        value = key.get_secret_value().strip()
        if not value:
            return None
        if not value.isascii() or not value.isprintable() or " " in value:
            raise ValueError("BYTEZ_API_KEY must contain visible ASCII characters only")
        return SecretStr(value)

    @field_validator("BYTEZ_API_URL")
    @classmethod
    def validate_bytez_api_url(cls, value: str) -> str:
        """Require TLS for requests carrying the provider credential."""
        url = value.strip()
        _parse_http_url(url, ("https",))
        return url.rstrip("/")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        """Accept an origin list as JSON or comma-separated environment text."""
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("ALLOWED_ORIGINS must be a JSON array") from None
        return [] if not value.strip() else value.split(",")

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, values: list[str]) -> list[str]:
        """Require explicit browser origins with no path."""
        origins = []
        for value in values:
            url = _parse_http_url(value.strip(), ("http", "https"))
            if url.path not in {"", "/"}:
                raise ValueError("An allowed origin must not contain a path")
            netloc = url.netloc.lower()
            default_port = 80 if url.scheme == "http" else 443
            if url.port == default_port:
                netloc, _, _ = netloc.rpartition(":")
            origins.append(f"{url.scheme}://{netloc}")
        return list(dict.fromkeys(origins))

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        """Reject unsafe settings when running in production."""
        if self.ENVIRONMENT.casefold() == "production":
            if self.DEBUG:
                raise ValueError("DEBUG cannot be enabled in production")
            if self.offline:
                raise ValueError("Production requires BYTEZ_API_KEY")
        return self
