"""Load and validate application settings from the environment."""

import json
from ipaddress import ip_address
from typing import Annotated, Self
from urllib.parse import SplitResult, urlsplit

from pydantic import (
    AliasChoices,
    Field,
    SecretStr,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.models.schemas import (
    QUERY_TEXT_MAX_LENGTH,
    QUERY_TEXT_MIN_LENGTH,
    GenerationProvider,
    GenerationSource,
)

OFFLINE_BYTEZ_KEY = "your_api_key_here"

_OPENAI_API_URL = "https://api.openai.com/v1"
_DEFAULT_MODELS: dict[GenerationProvider, str] = {
    "bytez": "Qwen/Qwen2-7B-Instruct",
    "openai": "gpt-4.1-mini",
    "ollama": "qwen2.5-coder:1.5b",
}


def _parse_http_url(value: str, schemes: tuple[str, ...]) -> SplitResult:
    """Validate a configured HTTP URL without leaking it in error messages."""
    if any(character.isspace() or not character.isprintable() for character in value):
        raise ValueError("URL must not contain whitespace or control characters")

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


def _is_loopback_host(host: str | None) -> bool:
    """Recognize literal loopback addresses and localhost without resolving DNS."""
    if host is None:
        return False
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    """Settings bound to an application instance."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    GENERATION_MODE: GenerationSource = "live"
    GENERATION_PROVIDER: GenerationProvider = "bytez"
    BYTEZ_API_KEY: SecretStr | None = None
    OPENAI_API_KEY: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("QUERYCRAFT_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    MODEL_NAME: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    BYTEZ_API_URL: str = "https://api.bytez.com/models/v2/openai/v1"
    OLLAMA_API_URL: str = "http://127.0.0.1:11434/v1"
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
        """Return whether local demo examples were explicitly requested."""
        key = self.BYTEZ_API_KEY
        return self.GENERATION_MODE == "demo" or (
            self.GENERATION_PROVIDER == "bytez"
            and key is not None
            and key.get_secret_value() == OFFLINE_BYTEZ_KEY
        )

    @property
    def model_name(self) -> str:
        """Return the configured model override or the selected provider default."""
        return self.MODEL_NAME or _DEFAULT_MODELS[self.GENERATION_PROVIDER]

    @property
    def provider_url(self) -> str:
        """Return the base URL for the selected provider."""
        if self.GENERATION_PROVIDER == "openai":
            return _OPENAI_API_URL
        if self.GENERATION_PROVIDER == "ollama":
            return self.OLLAMA_API_URL
        return self.BYTEZ_API_URL

    @property
    def provider_is_loopback(self) -> bool:
        """Return whether the provider URL names a loopback host."""
        return _is_loopback_host(urlsplit(self.provider_url).hostname)

    @property
    def live_key(self) -> SecretStr | None:
        """Return only the selected cloud provider's credential."""
        if self.GENERATION_PROVIDER == "openai":
            return self.OPENAI_API_KEY
        if self.GENERATION_PROVIDER == "ollama":
            return None
        key = self.BYTEZ_API_KEY
        if key is not None and key.get_secret_value() != OFFLINE_BYTEZ_KEY:
            return key
        return None

    @field_validator("BYTEZ_API_KEY", "OPENAI_API_KEY")
    @classmethod
    def validate_provider_key(cls, key: SecretStr | None, info: ValidationInfo) -> SecretStr | None:
        """Normalize an optional API key and ensure it can be sent in a header."""
        if key is None:
            return None
        value = key.get_secret_value().strip()
        if not value:
            return None
        if not value.isascii() or not value.isprintable() or " " in value:
            raise ValueError(f"{info.field_name} must contain visible ASCII characters only")
        return SecretStr(value)

    @field_validator("BYTEZ_API_URL")
    @classmethod
    def validate_bytez_api_url(cls, value: str) -> str:
        """Require TLS for requests carrying the provider credential."""
        url = value.strip()
        _parse_http_url(url, ("https",))
        return url.rstrip("/")

    @field_validator("OLLAMA_API_URL")
    @classmethod
    def validate_ollama_api_url(cls, value: str) -> str:
        """Permit unencrypted HTTP only when Ollama runs on loopback."""
        url = value.strip()
        parsed = _parse_http_url(url, ("http", "https"))
        if parsed.scheme == "http" and not _is_loopback_host(parsed.hostname):
            raise ValueError("OLLAMA_API_URL must use HTTPS for a non-loopback host")
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
                raise ValueError("Production does not allow demo generation")
            if self.GENERATION_PROVIDER != "ollama" and self.live_key is None:
                raise ValueError(f"Production requires {self.GENERATION_PROVIDER.upper()}_API_KEY")
        return self
