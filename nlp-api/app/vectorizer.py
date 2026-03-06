"""TF-IDF + KeyBERT 기반 VOD 텍스트 벡터화.

변경이력:
- TF-IDF 모델 영속화 추가: 서비스 재시작 시 자동 로드, 재학습 후 자동 저장
  - 저장 경로: TFIDF_MODEL_PATH 환경변수 (기본: /app/models/tfidf.pkl)
  - 자동 로드: nlp-api 기동 시 lifespan에서 load_tfidf() 호출
  - 자동 저장: fit_tfidf_on_corpus() 완료 시 save_tfidf() 자동 호출
"""
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import settings

log = structlog.get_logger()

# 싱글턴 (서비스 시작 시 초기화)
_keybert_model = None
_tfidf_vectorizer: Optional[TfidfVectorizer] = None
_tfidf_fitted = False

# TF-IDF 모델 저장 경로 (환경변수로 오버라이드 가능)
TFIDF_MODEL_PATH = os.environ.get("TFIDF_MODEL_PATH", "/app/models/tfidf.pkl")


def _get_keybert():
    global _keybert_model
    if _keybert_model is None:
        from keybert import KeyBERT
        log.info("keybert.loading", model=settings.keybert_model)
        _keybert_model = KeyBERT(model=settings.keybert_model)
        log.info("keybert.loaded")
    return _keybert_model


def get_or_create_tfidf() -> TfidfVectorizer:
    global _tfidf_vectorizer
    if _tfidf_vectorizer is None:
        _tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
    return _tfidf_vectorizer


# ──────────────────────────────────────────────────────────────
# TF-IDF 영속화: 저장 / 로드
# ──────────────────────────────────────────────────────────────

def save_tfidf() -> bool:
    """학습된 TF-IDF 모델을 pickle로 저장.

    Returns:
        저장 성공 여부
    """
    global _tfidf_vectorizer, _tfidf_fitted
    if not _tfidf_fitted or _tfidf_vectorizer is None:
        log.warning("tfidf.save_skipped: 아직 학습되지 않음")
        return False

    try:
        model_dir = Path(TFIDF_MODEL_PATH).parent
        model_dir.mkdir(parents=True, exist_ok=True)
        with open(TFIDF_MODEL_PATH, "wb") as f:
            pickle.dump(_tfidf_vectorizer, f, protocol=pickle.HIGHEST_PROTOCOL)
        size_kb = Path(TFIDF_MODEL_PATH).stat().st_size // 1024
        log.info("tfidf.saved", path=TFIDF_MODEL_PATH, size_kb=size_kb)
        return True
    except Exception as e:
        log.error("tfidf.save_failed", path=TFIDF_MODEL_PATH, error=str(e))
        return False


def load_tfidf() -> bool:
    """저장된 TF-IDF 모델을 로드. 파일이 없으면 False 반환.

    Returns:
        로드 성공 여부 (False면 /admin/vod_proc 재실행 필요)
    """
    global _tfidf_vectorizer, _tfidf_fitted
    if not Path(TFIDF_MODEL_PATH).exists():
        log.info(
            "tfidf.no_saved_model",
            path=TFIDF_MODEL_PATH,
            hint="/admin/vod_proc API 호출로 TF-IDF 재학습 필요",
        )
        return False

    try:
        with open(TFIDF_MODEL_PATH, "rb") as f:
            _tfidf_vectorizer = pickle.load(f)
        _tfidf_fitted = True
        vocab_size = len(_tfidf_vectorizer.vocabulary_) if hasattr(_tfidf_vectorizer, "vocabulary_") else "?"
        log.info("tfidf.loaded", path=TFIDF_MODEL_PATH, vocab_size=vocab_size)
        return True
    except Exception as e:
        log.error("tfidf.load_failed", path=TFIDF_MODEL_PATH, error=str(e))
        # 손상된 파일 삭제 후 재학습 유도
        try:
            Path(TFIDF_MODEL_PATH).unlink(missing_ok=True)
            log.warning("tfidf.corrupted_file_deleted", path=TFIDF_MODEL_PATH)
        except Exception:
            pass
        return False


def is_tfidf_ready() -> bool:
    """TF-IDF 모델이 사용 가능한 상태인지 반환."""
    return _tfidf_fitted and _tfidf_vectorizer is not None


# ──────────────────────────────────────────────────────────────


def build_source_text(title: str, genre: str, description: str, hash_tag: str, smry: str) -> str:
    """VOD 메타데이터를 단일 텍스트로 결합."""
    parts = [
        title or "",
        genre or "",
        description or "",
        hash_tag or "",
        smry or "",
    ]
    return " ".join(p for p in parts if p).strip()


def is_kids_genre(genre_code: Optional[str]) -> bool:
    """키즈/애니메이션 장르 여부 판단."""
    if not genre_code:
        return False
    upper = genre_code.upper()
    return any(k in upper for k in settings.kids_genre_list)


def extract_tfidf_vector(text: str, corpus: Optional[List[str]] = None) -> List[float]:
    """단일 텍스트의 TF-IDF 벡터 반환 (희소 배열 → dense list)."""
    vectorizer = get_or_create_tfidf()
    global _tfidf_fitted

    if not _tfidf_fitted:
        # 코퍼스가 없으면 단일 문서로 fit (임시)
        fit_corpus = corpus if corpus else [text]
        if text not in fit_corpus:
            fit_corpus = [text] + fit_corpus
        vectorizer.fit(fit_corpus)
        _tfidf_fitted = True

    vec = vectorizer.transform([text])
    return vec.toarray()[0].tolist()


def fit_tfidf_on_corpus(corpus: List[str]) -> None:
    """전체 VOD 코퍼스로 TF-IDF 재학습 후 자동 저장."""
    global _tfidf_fitted
    vectorizer = get_or_create_tfidf()
    vectorizer.fit(corpus)
    _tfidf_fitted = True
    log.info("tfidf.retrained", corpus_size=len(corpus))

    # 재학습 완료 즉시 저장 (서비스 재시작 대비)
    save_tfidf()


def extract_keybert_keywords(text: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """KeyBERT로 핵심 키워드 추출."""
    if not text.strip():
        return []
    try:
        model = _get_keybert()
        keywords = model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=top_n,
            use_mmr=True,
            diversity=0.5,
        )
        return [{"keyword": kw, "score": round(score, 4)} for kw, score in keywords]
    except Exception as e:
        log.warning("keybert.extract_failed", error=str(e))
        return []
