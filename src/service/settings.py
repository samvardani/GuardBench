from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Networking / Uvicorn
    uvicorn_host: str = "127.0.0.1"
    uvicorn_port: int = 8000
    uvicorn_workers: int = 1
    uvicorn_log_level: str = "info"
    uvicorn_timeout_keep_alive: int = 5

    # Service knobs
    predict_max_workers: int = 8
    predict_timeout_seconds: float = 2.0
    rate_limit_enabled: bool = True
    token_rate_limit: int = 60
    token_rate_window_seconds: int = 60
    redis_url: str | None = None
    log_level: str = "INFO"
    cors_allow_origins: str | None = None  # comma-separated list or None for "*"
    max_json_body_bytes: int = 1_048_576
    
    # Request & connection timeouts
    http_request_timeout_seconds: float = 30.0
    http_connect_timeout_seconds: float = 5.0
    http_read_timeout_seconds: float = 30.0
    
    # Database settings
    db_timeout_seconds: float = 5.0
    db_max_pool_size: int = 10

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    # Messaging / connectors
    kafka_brokers: str | None = None
    kafka_rest_proxy: str | None = None


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


__all__ = ["Settings", "get_settings"]

