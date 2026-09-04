from app.config import Settings, get_settings


def test_settings_have_sensible_defaults():
    settings = Settings(_env_file=None)
    assert settings.default_currency == "ARS"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("DEFAULT_CURRENCY", "USD")
    settings = Settings(_env_file=None)
    assert settings.default_currency == "USD"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
