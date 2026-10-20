"""Strongly-typed environment configuration (Spec A06, A07).

Every environment-dependent value lives here. Missing required values fail
fast at startup instead of surfacing as obscure runtime errors.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Learning Assistant Backend"
    env: str = Field(default="dev", validation_alias=AliasChoices("APP_ENV", "env"))
    api_v1_prefix: str = "/api/v1"

    # SQLite keeps local onboarding zero-dependency; Docker/Postgres overrides via env.
    database_url: str = "sqlite:///./dev.db"

    jwt_secret: str = Field(
        default="local-development-only-change-this-secret-5703",
        validation_alias=AliasChoices("SECRET_KEY", "jwt_secret"),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1, le=1440)

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "cors_origins"),
    )

    # Comma separated name:bool pairs. Unknown flags evaluate to False.
    feature_flags: str = "multi_workspace:false,lms_sync:false,agent_tools:false"

    seed_demo_users: bool = False
    model_mode: str = "mock"
    llm_provider: str = "mock"
    llm_model: str = "authored-extractive-v1"
    llm_api_base: str | None = None
    llm_api_key: str | None = Field(default=None, repr=False)
    model_config_encryption_key: str | None = Field(default=None, repr=False)
    model_config_key_file: str = ".secrets/model-config.key"
    storage_root: str = "./artifacts/storage"
    embedding_provider: str = "mock"
    embedding_model: str = "intfloat/e5-small-v2"
    embedding_revision: str = "main"
    embedding_dimension: int = Field(default=384, ge=1, le=8192)
    chat_retrieval_config: str | None = None
    max_upload_bytes: int = Field(default=536_870_912, ge=1, le=536_870_912)
    request_timeout_seconds: int = Field(default=180, ge=1, le=180)
    provider_timeout_seconds: int = Field(default=60, ge=1, le=60)
    max_provider_calls: int = Field(default=4, ge=1, le=4)
    model_window_tokens: int = Field(default=16384, ge=2048, le=2000000)
    model_output_tokens: int = Field(default=1024, ge=1, le=1024)
    worker_poll_seconds: float = Field(default=0.4, gt=0, le=60, allow_inf_nan=False)
    worker_stale_seconds: int = Field(default=240, ge=181, le=86400)
    mock_delay_seconds: float = Field(default=0.25, ge=0, le=5, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_environment(self):
        if self.env not in ("dev", "test", "demo") and (
            len(self.jwt_secret) < 32 or self.jwt_secret.startswith("local-development")
        ):
            raise ValueError(
                "A private SECRET_KEY of at least 32 characters is required outside development"
            )
        if self.model_mode not in ("mock", "live"):
            raise ValueError("MODEL_MODE must be mock or live")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def flags(self) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for pair in self.feature_flags.split(","):
            if ":" in pair:
                name, value = pair.split(":", 1)
                result[name.strip()] = value.strip().lower() in {"1", "true", "yes", "on"}
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
