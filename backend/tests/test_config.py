import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


def test_default_provider_url_uses_bytez_openai_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYTEZ_API_URL", raising=False)
    monkeypatch.delenv("GENERATION_PROVIDER", raising=False)
    settings = Settings(ENVIRONMENT="development", DEBUG=False, _env_file=None)

    assert settings.GENERATION_PROVIDER == "bytez"
    assert settings.provider_url == "https://api.bytez.com/models/v2/openai/v1"


def test_default_ollama_endpoint_is_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_API_URL", raising=False)
    settings = Settings(
        GENERATION_PROVIDER="ollama", ENVIRONMENT="development", DEBUG=False, _env_file=None
    )

    assert settings.provider_url == "http://127.0.0.1:11434/v1"


def test_configuration_keeps_secret_out_of_repr() -> None:
    bytez_secret = "synthetic-bytez-secret"
    openai_secret = "synthetic-openai-secret"
    settings = Settings(
        BYTEZ_API_KEY=SecretStr(bytez_secret),
        OPENAI_API_KEY=SecretStr(openai_secret),
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    for secret in (bytez_secret, openai_secret):
        assert secret not in repr(settings)
        assert secret not in settings.model_dump_json()


def test_app_specific_openai_key_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-conventional-key")
    monkeypatch.setenv("QUERYCRAFT_OPENAI_API_KEY", "synthetic-app-key")
    settings = Settings(
        GENERATION_PROVIDER="openai", ENVIRONMENT="development", DEBUG=False, _env_file=None
    )

    assert settings.live_key == SecretStr("synthetic-app-key")
    monkeypatch.delenv("QUERYCRAFT_OPENAI_API_KEY")
    settings = Settings(
        GENERATION_PROVIDER="openai", ENVIRONMENT="development", DEBUG=False, _env_file=None
    )

    assert settings.live_key == SecretStr("synthetic-conventional-key")


def test_generation_defaults_to_live_without_a_provider_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GENERATION_MODE", raising=False)
    settings = Settings(
        BYTEZ_API_KEY=None,
        GENERATION_PROVIDER="bytez",
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    assert settings.GENERATION_MODE == "live"
    assert not settings.offline
    assert settings.live_key is None


def test_legacy_demo_key_explicitly_enables_demo() -> None:
    settings = Settings(
        BYTEZ_API_KEY=SecretStr("your_api_key_here"),
        GENERATION_MODE="live",
        GENERATION_PROVIDER="bytez",
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    assert settings.offline
    assert settings.live_key is None


@pytest.mark.parametrize("provider", ["openai", "ollama"])
def test_legacy_bytez_demo_key_does_not_switch_other_providers(provider: str) -> None:
    settings = Settings(
        BYTEZ_API_KEY=SecretStr("your_api_key_here"),
        GENERATION_MODE="live",
        GENERATION_PROVIDER=provider,
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    assert not settings.offline


@pytest.mark.parametrize(
    ("generation_mode", "key"),
    [("live", "your_api_key_here"), ("demo", "synthetic-settings-secret")],
)
def test_production_rejects_demo_mode(generation_mode: str, key: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            BYTEZ_API_KEY=SecretStr(key),
            GENERATION_MODE=generation_mode,
            GENERATION_PROVIDER="bytez",
            ENVIRONMENT="production",
            DEBUG=False,
            _env_file=None,
        )


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            BYTEZ_API_KEY=SecretStr("synthetic-settings-secret"),
            GENERATION_MODE="live",
            GENERATION_PROVIDER="bytez",
            ENVIRONMENT="production",
            DEBUG=True,
            _env_file=None,
        )


def test_production_allows_keyless_ollama() -> None:
    settings = Settings(
        GENERATION_MODE="live",
        GENERATION_PROVIDER="ollama",
        BYTEZ_API_KEY=None,
        OPENAI_API_KEY=None,
        ENVIRONMENT="production",
        DEBUG=False,
        _env_file=None,
    )

    assert not settings.offline
    assert settings.live_key is None


@pytest.mark.parametrize(
    "url",
    [
        "http://provider.example/v1",
        "https://user@provider.example/v1",
        "https://provider.example/v1?option=value",
        "https://provider.example/v1#fragment",
    ],
)
def test_provider_url_rejects_unsafe_configuration(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(BYTEZ_API_URL=url, _env_file=None)


@pytest.mark.parametrize(
    ("url", "normalized"),
    [
        ("http://127.0.0.1:11434/v1/", "http://127.0.0.1:11434/v1"),
        ("http://localhost:11434/v1", "http://localhost:11434/v1"),
        ("http://[::1]:11434/v1", "http://[::1]:11434/v1"),
        ("https://ollama.example/v1", "https://ollama.example/v1"),
    ],
)
def test_ollama_allows_loopback_http_and_tls(url: str, normalized: str) -> None:
    settings = Settings(
        GENERATION_PROVIDER="ollama", OLLAMA_API_URL=url, ENVIRONMENT="development", _env_file=None
    )

    assert settings.provider_url == normalized


@pytest.mark.parametrize(
    "url",
    [
        "http://ollama.example/v1",
        "http://192.168.1.10:11434/v1",
        "https://user@ollama.example/v1",
        "https://ollama.example/v1?option=value",
        "https://ollama.example/v1#fragment",
    ],
)
def test_ollama_url_rejects_insecure_or_ambiguous_configuration(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(GENERATION_PROVIDER="ollama", OLLAMA_API_URL=url, _env_file=None)
