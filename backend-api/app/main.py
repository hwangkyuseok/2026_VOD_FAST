"""2026_TV Backend API — FastAPI 앱 진입점."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import channels, vod, customers, shopping, sessions, ad, commerce

# 로깅 초기화 — 앱 객체 생성 이전에 실행
setup_logging(
    service_name="backend-api",
    log_level=settings.log_level,
    log_dir=settings.log_dir,
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("api.start", env=settings.app_env)
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="2026_TV Backend API",
    description="차세대 미디어 플랫폼 — 채널·VOD·쇼핑·광고 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(channels.router, prefix="/api/v1")
app.include_router(vod.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(shopping.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(ad.router, prefix="/api/v1")
app.include_router(commerce.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "backend-api"}
