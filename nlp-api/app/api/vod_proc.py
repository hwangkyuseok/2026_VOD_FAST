"""/admin/vod_proc — VOD NLP 처리 및 추천 엔드포인트.

수정이력:
- TB_VOD_META 컬럼명: TITLE→TTL, THUMBNAIL_URL→THMBNL_PT (실제 DDL 기준)
- PostgreSQL alias를 명시적 소문자로 통일 (asyncpg 소문자 반환)
- update_user_profile: TB_VOD_LOG.ASSET_ID→ASSET, WATCH_TIME→USE_TMS
- 신규 유저 fallback: VIEW_COUNT 없음 → RATE(평점) 기반 정렬
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.vectorizer import (
    build_source_text,
    extract_keybert_keywords,
    extract_tfidf_vector,
    fit_tfidf_on_corpus,
    is_kids_genre,
)
from app.recommender import compute_user_vector, recommend_vod, compute_genre_profile

router = APIRouter(prefix="/admin", tags=["admin/nlp"])
log = structlog.get_logger()


class VodProcRequest(BaseModel):
    asset_ids: Optional[List[str]] = None  # None이면 전체 처리


class RecommendRequest(BaseModel):
    user_id: str
    top_n: int = 10


class RecommendResult(BaseModel):
    asset_id: str
    score: float
    reason: str
    title: Optional[str] = None
    genre: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_kids: bool = False


async def _process_single_vod(asset_id: str, db: AsyncSession) -> bool:
    """단일 VOD NLP 벡터화 처리."""
    # PostgreSQL은 unquoted alias를 소문자로 반환하므로 alias를 명시적으로 소문자로 통일
    result = await db.execute(
        text("""
            SELECT asset_id,
                   COALESCE(ttl,'') AS title,
                   COALESCE(genre,'') AS genre,
                   COALESCE(description,'') AS description,
                   COALESCE(hash_tag,'') AS hash_tag,
                   COALESCE(smry,'') AS smry
            FROM tb_vod_meta WHERE asset_id = :aid
        """),
        {"aid": asset_id},
    )
    row = result.mappings().first()
    if not row:
        return False

    source_text = build_source_text(
        row["title"], row["genre"], row["description"], row["hash_tag"], row["smry"]
    )
    tfidf_vec = extract_tfidf_vector(source_text)
    keywords = extract_keybert_keywords(source_text)
    kids = is_kids_genre(row["genre"])
    genre_code = (row["genre"] or "").upper()

    # UPSERT
    await db.execute(
        text("""
            INSERT INTO TB_VOD_NLP_VECTOR
                (ASSET_ID, SOURCE_TEXT, TFIDF_VECTOR, KEYBERT_KEYWORDS, GENRE_CODE, IS_KIDS_GENRE, MODEL_VERSION, UPDATED_AT)
            VALUES (:aid, :src, :vec::jsonb, :kw::jsonb, :gc, :ik, :mv, NOW())
            ON CONFLICT (ASSET_ID) DO UPDATE SET
                SOURCE_TEXT = EXCLUDED.SOURCE_TEXT,
                TFIDF_VECTOR = EXCLUDED.TFIDF_VECTOR,
                KEYBERT_KEYWORDS = EXCLUDED.KEYBERT_KEYWORDS,
                GENRE_CODE = EXCLUDED.GENRE_CODE,
                IS_KIDS_GENRE = EXCLUDED.IS_KIDS_GENRE,
                MODEL_VERSION = EXCLUDED.MODEL_VERSION,
                UPDATED_AT = NOW()
        """),
        {
            "aid": asset_id,
            "src": source_text,
            "vec": json.dumps(tfidf_vec),
            "kw": json.dumps(keywords),
            "gc": genre_code,
            "ik": "Y" if kids else "N",
            "mv": settings.model_version,
        },
    )

    # TB_VOD_META 업데이트 (schema_additions.sql에서 추가된 컬럼)
    await db.execute(
        text("UPDATE tb_vod_meta SET nlp_vector_updated_at = NOW() WHERE asset_id = :aid"),
        {"aid": asset_id},
    )
    return True


async def _run_vod_proc(asset_ids: Optional[List[str]], db: AsyncSession):
    """VOD NLP 배치 처리 (백그라운드)."""
    if asset_ids:
        target_ids = asset_ids
    else:
        result = await db.execute(text("SELECT asset_id FROM tb_vod_meta ORDER BY asset_id"))
        target_ids = [r[0] for r in result.fetchall()]

    # 전체 코퍼스로 TF-IDF 재학습 (TTL이 실제 컬럼명)
    corpus_result = await db.execute(
        text("""
            SELECT COALESCE(ttl,'') || ' ' || COALESCE(genre,'') || ' ' ||
                   COALESCE(description,'') || ' ' || COALESCE(smry,'') AS src
            FROM tb_vod_meta
        """)
    )
    corpus = [r[0] for r in corpus_result.fetchall() if r[0].strip()]
    if corpus:
        fit_tfidf_on_corpus(corpus)

    success, fail = 0, 0
    for aid in target_ids:
        try:
            ok = await _process_single_vod(aid, db)
            if ok:
                success += 1
        except Exception as e:
            log.error("vod_proc.failed", asset_id=aid, error=str(e))
            fail += 1

    await db.commit()
    log.info("vod_proc.complete", success=success, fail=fail)


@router.post("/vod_proc")
async def trigger_vod_proc(
    req: VodProcRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """VOD NLP 벡터화 트리거 (비동기 처리)."""
    background_tasks.add_task(_run_vod_proc, req.asset_ids, db)
    count = len(req.asset_ids) if req.asset_ids else "전체"
    return {"message": f"VOD NLP 처리 시작 ({count}개)", "status": "processing"}


@router.post("/recommend", response_model=List[RecommendResult])
async def get_personalized_recommendation(
    req: RecommendRequest,
    db: AsyncSession = Depends(get_db),
):
    """개인화 VOD 추천 (트랙 2) — 코사인 유사도 + 키즈 가중치."""
    # 유저 프로필 조회
    profile_result = await db.execute(
        text("""
            SELECT PROFILE_VECTOR, KIDS_BOOST_SCORE
            FROM TB_USER_PROFILE_VECTOR WHERE USER_ID = :uid
        """),
        {"uid": req.user_id},
    )
    profile = profile_result.mappings().first()

    if not profile or not profile["profile_vector"]:
        # 프로필 없는 신규 유저: 평점 높은 무료 VOD 반환
        # VIEW_COUNT 컬럼은 스키마에 없음 → RATE(평점) 기반 정렬
        result = await db.execute(
            text("""
                SELECT v.asset_id,
                       v.ttl AS title,
                       v.genre,
                       v.thmbnl_pt AS thumbnail_url,
                       CASE WHEN n.is_kids_genre = 'Y' THEN TRUE ELSE FALSE END AS is_kids
                FROM tb_vod_meta v
                LEFT JOIN tb_vod_nlp_vector n ON v.asset_id = n.asset_id
                WHERE v.is_free_yn = 'Y'
                ORDER BY COALESCE(v.rate, 0) DESC
                LIMIT :top_n
            """),
            {"top_n": req.top_n},
        )
        rows = result.mappings().all()
        return [
            RecommendResult(
                asset_id=r["asset_id"],
                score=1.0,
                reason="인기 콘텐츠 추천 (시청 이력 없음)",
                title=r.get("title"),
                genre=r.get("genre"),
                thumbnail_url=r.get("thumbnail_url"),
                is_kids=r.get("is_kids", False),
            )
            for r in rows
        ]

    user_vector = profile["profile_vector"]
    kids_boost = float(profile["kids_boost_score"])

    # VOD NLP 벡터 전체 조회 (소문자 alias 통일)
    vod_result = await db.execute(
        text("""
            SELECT n.asset_id,
                   n.tfidf_vector,
                   n.is_kids_genre,
                   v.genre,
                   v.ttl AS title,
                   v.thmbnl_pt AS thumbnail_url
            FROM tb_vod_nlp_vector n
            JOIN tb_vod_meta v ON n.asset_id = v.asset_id
            WHERE v.is_free_yn = 'Y'
        """)
    )
    vod_rows = vod_result.mappings().all()

    vod_vectors = [
        {
            "asset_id": r["asset_id"],
            "vector": r["tfidf_vector"],
            "is_kids": r["is_kids_genre"] == "Y",
            "genre": r.get("genre"),
            "title": r.get("title"),
            "thumbnail_url": r.get("thumbnail_url"),
        }
        for r in vod_rows
    ]

    recommended = recommend_vod(
        user_vector=user_vector,
        vod_vectors=vod_vectors,
        kids_boost_score=kids_boost,
        top_n=req.top_n,
    )

    # 썸네일 정보 보완 (thumbnail_url은 recommend 결과에 없으므로 vod_vectors에서 조회)
    asset_meta = {v["asset_id"]: v for v in vod_vectors}
    results = [
        RecommendResult(
            asset_id=r["asset_id"],
            score=r["score"],
            reason=r["reason"],
            title=r.get("title"),
            genre=r.get("genre"),
            thumbnail_url=asset_meta.get(r["asset_id"], {}).get("thumbnail_url"),
            is_kids=r.get("is_kids", False),
        )
        for r in recommended
    ]
    return results


@router.post("/update_user_profile")
async def update_user_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """유저 시청 이력 기반 프로필 벡터 갱신."""
    # 최근 시청 VOD 조회
    # TB_VOD_LOG: PK는 srl_no+p_mt, 콘텐츠 ID는 'asset'(not asset_id), 시청시간은 use_tms
    # TB_VOD_LOG와 TB_VOD_META 조인: l.asset = v.asset_id
    vod_result = await db.execute(
        text("""
            SELECT n.tfidf_vector,
                   v.genre,
                   COALESCE(l.use_tms, 1) AS watch_sec
            FROM tb_vod_log l
            JOIN tb_vod_meta v ON l.asset = v.asset_id
            JOIN tb_vod_nlp_vector n ON v.asset_id = n.asset_id
            WHERE l.user_id = :uid
            ORDER BY l.strt_dt DESC
            LIMIT 50
        """),
        {"uid": user_id},
    )
    rows = vod_result.mappings().all()

    if not rows:
        return {"message": "시청 이력이 없습니다.", "user_id": user_id}

    vectors = [r["tfidf_vector"] for r in rows if r["tfidf_vector"]]
    genre_list = [r["genre"] for r in rows if r.get("genre")]
    watch_times = [float(r.get("watch_sec") or 1) for r in rows]

    if not vectors:
        return {"message": "벡터화된 시청 이력이 없습니다.", "user_id": user_id}

    user_vector = compute_user_vector(vectors, weights=watch_times)
    genre_profile = compute_genre_profile(genre_list)

    # 키즈 비율 계산 → boost_score 산정
    kids_count = sum(
        1 for r in rows
        if r.get("genre") and is_kids_genre(r["genre"])
    )
    kids_ratio = kids_count / len(rows) if rows else 0
    # 비즈니스 룰: 최소 0.1 보장
    kids_boost = max(0.1, min(1.0, kids_ratio + settings.kids_boost_score))

    await db.execute(
        text("""
            INSERT INTO TB_USER_PROFILE_VECTOR
                (USER_ID, PROFILE_VECTOR, FAVORITE_GENRES, KIDS_BOOST_SCORE, TOTAL_WATCH_SEC, UPDATED_AT)
            VALUES (:uid, :vec::jsonb, :genres::jsonb, :kids, :total_sec, NOW())
            ON CONFLICT (USER_ID) DO UPDATE SET
                PROFILE_VECTOR = EXCLUDED.PROFILE_VECTOR,
                FAVORITE_GENRES = EXCLUDED.FAVORITE_GENRES,
                KIDS_BOOST_SCORE = EXCLUDED.KIDS_BOOST_SCORE,
                TOTAL_WATCH_SEC = EXCLUDED.TOTAL_WATCH_SEC,
                UPDATED_AT = NOW()
        """),
        {
            "uid": user_id,
            "vec": json.dumps(user_vector),
            "genres": json.dumps(genre_profile),
            "kids": round(kids_boost, 3),
            "total_sec": int(sum(watch_times)),
        },
    )
    await db.commit()
    return {"message": "유저 프로필 벡터 갱신 완료", "user_id": user_id, "kids_boost": kids_boost}
