"""광고 삽입 최적 타임스탬프 계산 — 저움직임 구간 선정."""
from typing import Any, Dict, List

import structlog

log = structlog.get_logger()


def calculate_insertion_points(
    scenes: List[Dict[str, Any]],
    min_scene_duration: float = 5.0,
    max_points: int = 5,
) -> List[Dict[str, Any]]:
    """씬 목록에서 광고 삽입 최적 구간 선정.

    전략:
    1. 씬 전환 직후 구간 (장면 변화 최소 = 이탈율 낮음)
    2. 씬 지속시간 기반 저움직임 판단 (길수록 정적인 씬)
    3. 영상 전반부/후반부 배분

    Args:
        scenes: SceneSegment 딕셔너리 목록
        min_scene_duration: 최소 씬 길이 필터 (초)
        max_points: 최대 삽입 포인트 수

    Returns:
        [{"timestamp_sec", "confidence", "motion_score", "insert_reason"}, ...]
    """
    if not scenes:
        return []

    # 유효 씬 필터링 (너무 짧은 씬 제외)
    valid_scenes = [
        s for s in scenes
        if (s.get("end_time", 0) - s.get("start_time", 0)) >= min_scene_duration
    ]

    if not valid_scenes:
        valid_scenes = scenes

    # 씬 길이 정규화 → motion_score (짧을수록 움직임 많음 = 점수 낮음)
    durations = [s.get("end_time", 0) - s.get("start_time", 0) for s in valid_scenes]
    max_dur = max(durations) if durations else 1.0

    candidates = []
    for scene, dur in zip(valid_scenes, durations):
        start = scene.get("start_time", 0)
        end = scene.get("end_time", 0)

        # motion_score: 낮을수록 저움직임 (0.0~1.0 역산)
        motion_score = 1.0 - (dur / max_dur)
        confidence = 1.0 - motion_score  # 높을수록 적합

        # 삽입 포인트: 씬 시작 직후 1초 (씬 전환 후 자연스러운 타이밍)
        timestamp = round(start + 1.0, 3)

        candidates.append({
            "timestamp_sec": timestamp,
            "confidence": round(confidence, 3),
            "motion_score": round(motion_score, 4),
            "insert_reason": _classify_reason(motion_score, dur),
        })

    # confidence 내림차순 정렬 후 상위 max_points 반환
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    selected = candidates[:max_points]

    # 타임스탬프 순서로 재정렬
    selected.sort(key=lambda x: x["timestamp_sec"])

    log.info("insertion_points.calculated", count=len(selected))
    return selected


def _classify_reason(motion_score: float, duration: float) -> str:
    """삽입 사유 코드 분류."""
    if motion_score < 0.3:
        return "LOW_MOTION"
    elif duration > 10.0:
        return "SCENE_BREAK"
    else:
        return "QUIET_MOMENT"
