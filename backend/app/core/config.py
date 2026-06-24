from functools import lru_cache
from typing import List
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    BASE_DOMAIN: str = "cctvamc.local"

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Column-level encryption (Fernet). If unset, a key is derived from
    # JWT_SECRET_KEY so dev/test work without extra config.
    ENCRYPTION_KEY: str = ""

    # Per-tenant/IP API rate limiting (requests per window). 0 disables.
    RATE_LIMIT_PER_MINUTE: int = 0

    # Object storage
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "cctv-media"

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # SMS / WhatsApp
    SMS_PROVIDER_URL: str = ""
    SMS_PROVIDER_API_KEY: str = ""
    WHATSAPP_API_URL: str = ""
    WHATSAPP_API_KEY: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # CORS
    CORS_ORIGINS: List[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
