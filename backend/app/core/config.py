from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://luma:luma_local_only@localhost:5432/luma"
    secret_key: str = "development-only-replace-with-at-least-32-random-characters"
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    access_minutes: int = 15
    refresh_days: int = 30
    storage_backend: str = "local"
    media_root: Path = Path("var/media")
    mail_backend: str = "file"
    mail_root: Path = Path("var/mail")
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Luma <noreply@example.com>"
    smtp_tls: bool = True
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    redis_url: str = ""
    upload_max_mb: int = 30
    rate_limit_enabled: bool = True
    log_level: str = "INFO"

    @property
    def origins(self):
        return [v.strip().rstrip("/") for v in self.allowed_origins.split(",") if v.strip()]

    @model_validator(mode="after")
    def validate_production(self):
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict or none")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None requires Secure cookies")
        if "*" in self.origins:
            raise ValueError("Explicit origins are required")
        if self.environment == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith("development-"):
                raise ValueError("Set a strong SECRET_KEY")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
            if not self.cookie_secure or not all(x.startswith("https://") for x in self.origins):
                raise ValueError("Production requires HTTPS origins and secure cookies")
            if self.storage_backend != "s3" or not self.s3_bucket:
                raise ValueError("Production requires private S3 storage")
            if self.mail_backend != "smtp" or not self.smtp_host or not self.redis_url:
                raise ValueError("Production requires SMTP and Redis")
        return self


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
