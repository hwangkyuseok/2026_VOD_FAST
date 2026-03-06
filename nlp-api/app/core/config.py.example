from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = ""
    db_host: str = "YOUR_DB_HOST_IP"
    db_port: int = 5432
    db_name: str = "YOUR_DB_NAME"
    db_user: str = "YOUR_DB_USER"
    db_password: str = ""  # 반드시 .env에서 주입 — 기본값 없음 (보안)

    redis_url: str = "redis://redis:6379/0"
    log_level: str = "INFO"
    log_dir: str = "/app/logs"

    # NLP 설정
    keybert_model: str = "snunlp/KR-ELECTRA-discriminator"
    kids_genre_codes: str = "KIDS,ANIME,ANIMATION,어린이,애니메이션,키즈"
    kids_boost_score: float = 0.3
    personalized_vod_count: int = 10
    model_version: str = "v1.0"

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
    def kids_genre_list(self) -> List[str]:
        return [c.strip().upper() for c in self.kids_genre_codes.split(",")]


settings = Settings()
