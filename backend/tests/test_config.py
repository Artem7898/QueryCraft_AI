import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


def test_default_provider_url_uses_bytez_openai_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BYTEZ_API_URL", raising=False)
    settings = Settings(ENVIRONMENT="development", DEBUG=False, _env_file=None)

    assert settings.BYTEZ_API_URL == "https://api.bytez.com/models/v2/openai/v1"


def test_configuration_keeps_secret_out_of_repr() -> None:
    secret = "synthetic-settings-secret"
    settings = Settings(
        BYTEZ_API_KEY=SecretStr(secret),
        ENVIRONMENT="development",
        DEBUG=False,
        _env_file=None,
    )

    assert secret not in repr(settings)
    assert secret not in settings.model_dump_json()


def test_production_rejects_offline_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            BYTEZ_API_KEY=SecretStr("your_api_key_here"),
            ENVIRONMENT="production",
            DEBUG=False,
            _env_file=None,
        )


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            BYTEZ_API_KEY=SecretStr("synthetic-settings-secret"),
            ENVIRONMENT="production",
            DEBUG=True,
            _env_file=None,
        )


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
