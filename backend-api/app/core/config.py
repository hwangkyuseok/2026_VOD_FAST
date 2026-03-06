from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── PostgreSQL ─────────────────────────────────────────────
    database_url: str = ""
    db_host: str = "YOUR_DB_HOST_IP"
    db_port: int = 5432
    db_name: str = "YOUR_DB_NAME"
    db_user: str = "YOUR_DB_USER"
    db_password: str = ""

    # ── Redis ──────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: str = "*"

    # ── 서비스 ────────────────────────────────────────────────
    app_env: str = "production"
    log_level: str = "INFO"
    log_dir: str = "/app/logs"

    # ── NLP API 연동 ──────────────────────────────────────────
    nlp_api_url: str = "http://nlp-api:8001"

    # ── 채널 설정 ─────────────────────────────────────────────
    channel_count: int = 30
    channel_zap_delay_ms: int = 500

    # ── VOD 추천 ─────────────────────────────────────────────
    personalized_vod_count: int = 10
    weekly_free_vod_count: int = 10

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def allow_origins(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
