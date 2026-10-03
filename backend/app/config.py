from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # asyncpg is used at runtime; Alembic migrations still run synchronously via
    # sync_database_url below (asyncpg has no sync DBAPI counterpart).
    DATABASE_URL: str = "postgresql+asyncpg://phishsim:change-me@localhost:5432/phishing_sim"

    REDIS_URL: str = "redis://localhost:6379/0"
    # Blank by default: filled from REDIS_URL below unless explicitly set, so a
    # managed-Redis deploy (e.g. Railway) only needs REDIS_URL, never a stray
    # localhost broker.
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def _coerce_async_driver(cls, v: str) -> str:
        # Managed Postgres (Railway/Heroku/etc.) hands out "postgres://" or
        # "postgresql://" URLs; SQLAlchemy's async engine needs the asyncpg
        # driver named explicitly. Normalize so the injected URL just works.
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @model_validator(mode="after")
    def _default_celery_to_redis(self) -> "Settings":
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        return self

    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Fernet key (32 url-safe base64-encoded bytes) used to encrypt SMTP
    # passwords and captured credentials at rest. Generate your own with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = "n6R55QZWgRYbjPbk9yMtAw7RV-dfEjrKviwv93OwBRc="

    # HMAC key signing CampaignTarget.tracking_sig - keep separate from SECRET_KEY
    # so rotating one doesn't invalidate the other.
    TRACKING_HMAC_SECRET: str = "change-me-tracking-hmac-secret"

    # Optional API key for an external text-generation provider, reserved for a
    # future template-copy helper. Kept out of source and read from the
    # environment; blank by default so nothing depends on it being set.
    LLM_API_KEY: str = ""

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_DEFAULT_SENDER: str = "training@example.internal"

    APP_BASE_URL: str = "http://localhost:8080"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


settings = Settings()
