"""코사인 유사도 기반 VOD 추천 엔진.

비즈니스 룰:
- 키즈·애니메이션 장르는 항상 추천 풀에 포함 (배제 금지)
- kids_boost_score 최소 0.1 보장
"""
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings

log = structlog.get_logger()


def _ensure_min_kids_boost(score: float) -> float:
    """비즈니스 룰: kids_boost_score 최소 0.1 강제."""
    return max(score, 0.1)


def compute_user_vector(
    watch_vectors: List[List[float]],
    weights: Optional[List[float]] = None,
) -> List[float]:
    """시청 이력 벡터들의 가중 평균으로 유저 프로필 벡터 생성."""
    if not watch_vectors:
        return []

    arr = np.array(watch_vectors, dtype=float)
    if weights:
        w = np.array(weights, dtype=float)
        w = w / w.sum()
        user_vec = np.average(arr, axis=0, weights=w)
    else:
        user_vec = arr.mean(axis=0)

    return user_vec.tolist()


def recommend_vod(
    user_vector: List[float],
    vod_vectors: List[Dict[str, Any]],
    kids_boost_score: float = 0.3,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """코사인 유사도 + 키즈 가중치 적용 VOD 추천.

    Args:
        user_vector: 유저 프로필 벡터 (TF-IDF 공간)
        vod_vectors: [{"asset_id", "vector", "is_kids", "genre", "title"}, ...]
        kids_boost_score: 키즈/애니 가중치 (최소 0.1 보장)
        top_n: 반환할 추천 개수

    Returns:
        [{"asset_id", "score", "reason"}, ...] 정렬된 추천 목록
    """
    kids_boost = _ensure_min_kids_boost(kids_boost_score)

    if not user_vector or not vod_vectors:
        log.warning("recommend_vod.empty_input")
        return []

    user_arr = np.array(user_vector, dtype=float).reshape(1, -1)

    results = []
    for item in vod_vectors:
        vec = item.get("vector")
        if not vec:
            continue

        vod_arr = np.array(vec, dtype=float).reshape(1, -1)

        # 차원 불일치 시 패딩
        if user_arr.shape[1] != vod_arr.shape[1]:
            target_dim = max(user_arr.shape[1], vod_arr.shape[1])
            if user_arr.shape[1] < target_dim:
                user_arr = np.pad(user_arr, ((0, 0), (0, target_dim - user_arr.shape[1])))
            if vod_arr.shape[1] < target_dim:
                vod_arr = np.pad(vod_arr, ((0, 0), (0, target_dim - vod_arr.shape[1])))

        base_score = float(cosine_similarity(user_arr, vod_arr)[0][0])

        # 키즈·애니메이션 가중치 적용 (절대 배제 금지)
        if item.get("is_kids"):
            final_score = base_score + kids_boost
            reason = f"키즈/애니메이션 선호 가중치 적용 (boost={kids_boost:.2f})"
        else:
            final_score = base_score
            reason = f"시청 이력 기반 유사도 {base_score:.3f}"

        results.append({
            "asset_id": item["asset_id"],
            "score": round(final_score, 4),
            "base_score": round(base_score, 4),
            "is_kids": item.get("is_kids", False),
            "genre": item.get("genre"),
            "title": item.get("title"),
            "reason": reason,
        })

    # 점수 내림차순 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def compute_genre_profile(genre_list: List[str]) -> List[Dict[str, Any]]:
    """장르 목록에서 선호 장르 프로필 생성."""
    from collections import Counter
    counts = Counter(genre_list)
    total = sum(counts.values()) or 1
    return [
        {"genre": genre, "score": round(count / total, 4)}
        for genre, count in counts.most_common(10)
    ]
