from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://bolsillito:bolsillito@localhost:5432/bolsillito"
    default_currency: str = "ARS"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Clave de firma de los JWT de sesión. El default solo sirve para dev -- en producción hay
    # que sobreescribirla con una variable de entorno propia (ej. `openssl rand -hex 32`),
    # si no cualquiera puede firmar tokens válidos con esta clave pública en el repo.
    secret_key: str = "dev-only-insecure-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 días


@lru_cache
def get_settings() -> Settings:
    return Settings()
