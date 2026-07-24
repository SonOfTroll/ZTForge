"""
Application settings with environment validation.

Uses Pydantic Settings to enforce required config at startup rather than
failing at runtime. Feature flags control MVP-level features that aren't
fully production-ready yet.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project-root .env regardless of the working directory at runtime
_ENV_FILE = Path(__file__).parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_name: str = "ZTForge"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    secret_key: str = Field(min_length=16)
    allowed_origins: str | list[str] = ["http://localhost:5173"]
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Database ─────────────────────────────────────────────
    database_url: PostgresDsn

    # ── Redis ────────────────────────────────────────────────
    redis_url: RedisDsn = "redis://redis:6379/0"  # type: ignore[assignment]

    # ── Keycloak ─────────────────────────────────────────────
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "ztforge"
    keycloak_client_id: str = "ztforge-app"
    keycloak_client_secret: str = ""

    # ── OPA ──────────────────────────────────────────────────
    opa_url: str = "http://opa:8181"

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_per_second: int = 10

    # ── Feature Flags ────────────────────────────────────────
    # MVP flags — disable in prod until battle-tested
    enable_breach_simulation: bool = True
    enable_policy_hub: bool = True
    enable_enforcement_demo: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def keycloak_issuer_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/certs"
        )

    @property
    def keycloak_token_url(self) -> str:
        return (
            f"{self.keycloak_url}/realms/{self.keycloak_realm}"
            "/protocol/openid-connect/token"
        )


@lru_cache
def get_settings() -> Settings:
    """Singleton settings — cached after first load."""
    return Settings()  # type: ignore[call-arg]
