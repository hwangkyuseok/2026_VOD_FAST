"""2026_TV NLP API — FastAPI 앱 진입점."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.vod_proc import router as vod_proc_router

# 로깅 초기화 — 앱 객체 생성 이전에 실행
setup_logging(
    service_name="nlp-api",
    log_level=settings.log_level,
    log_dir=settings.log_dir,
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """서비스 기동 시 모델 사전 로드.

    1. TF-IDF: 저장된 pickle 자동 로드 (없으면 /admin/vod_proc 호출 필요)
    2. KeyBERT: HuggingFace 모델 실제 로드 (첫 요청 지연 방지 워밍업)
    """
    log.info("api.start", service="nlp-api", model=settings.keybert_model)

    # 1. TF-IDF 저장모델 로드
    from app.vectorizer import load_tfidf, is_tfidf_ready
    tfidf_ok = load_tfidf()
    if tfidf_ok:
        log.info("api.tfidf_loaded")
    else:
        log.warning(
            "api.tfidf_not_ready",
            hint="POST /admin/vod_proc 호출하면 TF-IDF 학습 후 자동 저장됩니다",
        )

    # 2. KeyBERT 워밍업
    try:
        from app.vectorizer import _get_keybert
        _get_keybert()
        log.info("api.keybert_warmup_done", model=settings.keybert_model)
    except Exception as e:
        log.warning("api.keybert_warmup_failed", error=str(e))

    yield
    log.info("api.shutdown")


app = FastAPI(
    title="2026_TV NLP API",
    description="VOD 추천 NLP 엔진 — TF-IDF + KeyBERT + 코사인 유사도",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vod_proc_router)


@app.get("/health")
async def health_check():
    from app.vectorizer import is_tfidf_ready
    return {
        "status": "ok",
        "service": "nlp-api",
        "model": settings.keybert_model,
        "tfidf_ready": is_tfidf_ready(),
    }
