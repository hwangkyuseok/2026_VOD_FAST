"""2026_TV Ad Batch Worker — APScheduler 기반 FAST 광고 생성 파이프라인.

Weekly VOD Curation v2:
  - 3단계 CTE 쿼리로 슬롯 기반 선정 (KIDS 3 + DOCU_LIFE 4 + ENT 2 + ETC 1)
  - SELECTION_REASON: SLOT_KIDS / SLOT_DOCU / SLOT_ENT / SLOT_ETC
  - 이전 주 IS_FREE_YN 자동 복원 (v1 버그 수정)
  - 슬롯 미달 시 경고 로그 출력
"""
import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

import structlog
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine, text

from app.logging_setup import setup_logging
from app.scene_detector import detect_scenes
from app.vision_analyzer import analyze_keyframe
from app.ad_generator import generate_image_ad, generate_video_ad
from app.timestamp_calculator import calculate_insertion_points
from app.seasonal_themes import build_seasonal_case_when, SLOT_REASON_MAP

# 로깅 초기화 (모듈 임포트 직후, DB 연결 이전)
setup_logging(
    service_name="ad-batch",
    log_level=os.environ.get("LOG_LEVEL", "INFO"),
    log_dir=os.environ.get("LOG_DIR", "/app/logs"),
)

log = structlog.get_logger()

DATABASE_URL = os.environ["DATABASE_URL"]
AD_BATCH_CRON = os.environ.get("AD_BATCH_CRON", "0 2 * * 1")
WEEKLY_FREE_VOD_COUNT = int(os.environ.get("WEEKLY_FREE_VOD_COUNT", "10"))
VOD_SOURCE_DIR = os.environ.get("VOD_SOURCE_DIR", "/app/data/vod")
AD_ASSET_DIR = os.environ.get("AD_ASSET_DIR", "/app/data/ad_assets")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y%m%d")


def _restore_previous_free_vod(conn, current_week: str) -> None:
    """이전 주 무료로 변경된 VOD의 IS_FREE_YN을 'N' 으로 복원한다.

    현재 주(current_week)에도 선정된 VOD는 복원 대상에서 제외한다.
    이 함수는 새 배치 선정 직전에 호출해야 한다.
    """
    conn.execute(
        text("""
            UPDATE TB_VOD_META m
            SET IS_FREE_YN = 'N', FAST_AD_ELIGIBLE_YN = 'N'
            WHERE m.ASSET_ID IN (
                SELECT ASSET_ID FROM TB_WEEKLY_FREE_VOD
                WHERE WEEK_START_YMD < :current_week AND IS_ACTIVE = 'N'
            )
            AND m.ASSET_ID NOT IN (
                SELECT ASSET_ID FROM TB_WEEKLY_FREE_VOD
                WHERE WEEK_START_YMD = :current_week AND IS_ACTIVE = 'Y'
            )
        """),
        {"current_week": current_week},
    )
    log.info("weekly_vod.restore_previous_done", current_week=current_week)


def select_weekly_free_vod() -> List[Dict[str, Any]]:
    """슬롯 기반 3단계 CTE 쿼리로 금주 무료 VOD 10개를 선정한다 (v2).

    슬롯 배분:
        KIDS          ≤ 3개  (SELECTION_REASON = SLOT_KIDS)
        DOCU_LIFE     ≤ 4개  (SELECTION_REASON = SLOT_DOCU)
        ENTERTAINMENT ≤ 2개  (SELECTION_REASON = SLOT_ENT)
        ETC           ≤ 1개  (SELECTION_REASON = SLOT_ETC)

    하드 필터:
        USE_FL = 1, SVC_APY_FL = 1, THMBNL_FL = 1,
        IS_FREE_YN = 'N', DISP_RTM >= '00:20:00'

    소프트 점수:
        IS_HOT_FL +15, 고화질 +10, 키즈 1화 +15,
        4060 키워드 +20, 월별 시즌 테마 +30

    반환 딕셔너리 키: ASSET_ID, TTL, GENRE, slot_group, selection_score, SMRY
    """
    week_start = _current_week_start()

    # 1. 이전 주 IS_FREE_YN 복원 (v1 버그 수정)
    with engine.begin() as conn:
        _restore_previous_free_vod(conn, week_start)

    # 2. 기존 금주 VOD 비활성화
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE TB_WEEKLY_FREE_VOD SET IS_ACTIVE = 'N', UPDATED_AT = NOW() WHERE WEEK_START_YMD = :w"),
            {"w": week_start},
        )

    # 3. v2 CTE 쿼리로 슬롯 기반 10개 선정
    seasonal_case = build_seasonal_case_when()

    query = text(f"""
        WITH filtered_data AS (
            SELECT
                ASSET_ID,
                TTL,
                EPSD_NM,
                GENRE,
                SMRY,
                -- 1. 기본 가점 (인기작, 고화질)
                (CASE WHEN IS_HOT_FL = 1 THEN 15 ELSE 0 END) +
                (CASE WHEN SCREEN_TP IN ('HD', 'FHD', 'UHD') THEN 10 ELSE 0 END) +

                -- 2. 키즈 정주행 유도 가점 (키즈/애니 장르 + 1화)
                (CASE WHEN (GENRE LIKE '%키즈%' OR GENRE LIKE '%애니%') AND EPSD_NO = 1 THEN 15 ELSE 0 END) +

                -- 3. 4060 타겟 키워드 가점 (PostgreSQL 정규표현식)
                (CASE WHEN SMRY ~ '(건강|자연인|고향|밥상|다큐|트로트)' THEN 20 ELSE 0 END) +

                -- 4. 월별 시즌 테마 가점 (seasonal_themes.py 자동 생성)
{seasonal_case} AS total_score,

                -- 5. 슬롯 그룹 분류
                CASE
                    WHEN GENRE LIKE '%키즈%' OR GENRE LIKE '%애니%' THEN 'KIDS'
                    WHEN GENRE LIKE '%예능%' OR GENRE LIKE '%연예/오락%' THEN 'ENTERTAINMENT'
                    WHEN GENRE LIKE '%다큐%' OR GENRE LIKE '%교양%' THEN 'DOCU_LIFE'
                    ELSE 'ETC'
                END AS slot_group,

                SUPER_ASSET_NM,
                RLSE_YEAR,
                EPSD_NO

            FROM TB_VOD_META
            -- [Hard Filter] 품질 보장 필수 조건
            WHERE USE_FL = 1
              AND SVC_APY_FL = 1
              AND THMBNL_FL = 1
              AND IS_FREE_YN = 'N'           -- 유료 VOD에서만 선정
              AND DISP_RTM >= '00:20:00'     -- 20분 미만 자투리 제외
        ),
        deduplicated_data AS (
            -- [중복 제거] 시리즈 도배 방지: SUPER_ASSET_NM 기준 최고점 1개만
            SELECT
                *,
                ROW_NUMBER() OVER(
                    PARTITION BY COALESCE(SUPER_ASSET_NM, TTL)
                    ORDER BY total_score DESC, RLSE_YEAR DESC, EPSD_NO ASC
                ) AS series_rn
            FROM filtered_data
        ),
        ranked_slots AS (
            -- [슬롯 내 순위] 각 슬롯 그룹 안에서 점수순 순위
            SELECT
                *,
                ROW_NUMBER() OVER(
                    PARTITION BY slot_group
                    ORDER BY total_score DESC
                ) AS slot_rn
            FROM deduplicated_data
            WHERE series_rn = 1   -- 시리즈 중복 제거된 1위만
        )
        -- [최종 10개 추출] 슬롯 비율 적용
        SELECT
            ASSET_ID,
            TTL,
            GENRE,
            slot_group,
            total_score AS selection_score,
            SMRY
        FROM ranked_slots
        WHERE (slot_group = 'KIDS'          AND slot_rn <= 3)
           OR (slot_group = 'DOCU_LIFE'     AND slot_rn <= 4)
           OR (slot_group = 'ENTERTAINMENT' AND slot_rn <= 2)
           OR (slot_group = 'ETC'           AND slot_rn <= 1)
        ORDER BY
            CASE slot_group
                WHEN 'KIDS'          THEN 1
                WHEN 'DOCU_LIFE'     THEN 2
                WHEN 'ENTERTAINMENT' THEN 3
                ELSE 4
            END,
            total_score DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        vods = [dict(r._mapping) for r in result.fetchall()]

    if not vods:
        log.warning("weekly_vod.no_candidates")
        return []

    # 4. TB_WEEKLY_FREE_VOD 신규 삽입 + IS_FREE_YN 갱신
    with engine.begin() as conn:
        for rank, vod in enumerate(vods, 1):
            slot_group = vod.get("slot_group", "ETC")
            selection_reason = SLOT_REASON_MAP.get(slot_group, "SLOT_ETC")
            conn.execute(
                text("""
                    INSERT INTO TB_WEEKLY_FREE_VOD
                        (ID, WEEK_START_YMD, ASSET_ID, RANK_NO, SELECTION_SCORE, SELECTION_REASON, AD_PIPELINE_STATUS)
                    VALUES (gen_random_uuid(), :w, :aid, :rank, :score, :reason, 'PENDING')
                    ON CONFLICT (WEEK_START_YMD, ASSET_ID) DO UPDATE SET
                        RANK_NO = EXCLUDED.RANK_NO,
                        SELECTION_SCORE = EXCLUDED.SELECTION_SCORE,
                        SELECTION_REASON = EXCLUDED.SELECTION_REASON,
                        AD_PIPELINE_STATUS = 'PENDING',
                        IS_ACTIVE = 'Y',
                        UPDATED_AT = NOW()
                """),
                {
                    "w": week_start,
                    "aid": vod["ASSET_ID"],
                    "rank": rank,
                    "score": float(vod["selection_score"]),
                    "reason": selection_reason,
                },
            )
        # IS_FREE_YN + FAST_AD_ELIGIBLE_YN 갱신
        for vod in vods:
            conn.execute(
                text("UPDATE TB_VOD_META SET IS_FREE_YN = 'Y', FAST_AD_ELIGIBLE_YN = 'Y' WHERE ASSET_ID = :aid"),
                {"aid": vod["ASSET_ID"]},
            )

    log.info("weekly_vod.selected", week=week_start, count=len(vods))
    return vods


def run_fast_ad_pipeline(vod: Dict[str, Any]) -> None:
    """단일 VOD에 대한 FAST 광고 파이프라인 실행.

    1단계: PySceneDetect 씬 분할
    2단계: YOLO 비전 분석 → vision_tags
    3단계: 생성형 AI 광고 에셋 생성
    4단계: 삽입 타임스탬프 계산 → DB 저장
    """
    asset_id = vod["ASSET_ID"]
    vod_path = str(Path(VOD_SOURCE_DIR) / f"{asset_id}.mp4")
    work_dir = str(Path(AD_ASSET_DIR) / "work" / asset_id)
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    log.info("pipeline.start", asset_id=asset_id)

    # ── 상태 업데이트: IN_PROGRESS ─────────────────────────────
    week_start = _current_week_start()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE TB_WEEKLY_FREE_VOD SET AD_PIPELINE_STATUS = 'IN_PROGRESS', UPDATED_AT = NOW() WHERE WEEK_START_YMD = :w AND ASSET_ID = :aid"),
            {"w": week_start, "aid": asset_id},
        )

    try:
        # ── 1단계: 씬 분할 ───────────────────────────────────────
        if Path(vod_path).exists():
            scenes = detect_scenes(vod_path, work_dir)
        else:
            log.warning("pipeline.no_vod_file", path=vod_path, asset_id=asset_id)
            # VOD 파일 없음 → 더미 씬으로 계단 진행 (API 키 있으면 플레이스홀더 생성 가능)
            from app.scene_detector import SceneSegment
            scenes = [SceneSegment(0, 0.0, 10.0, 0, 300, None)]  # dummy 1개

        # ── 2단계: 비전 분석 ─────────────────────────────────────
        all_keywords = []
        scene_dicts = []
        for seg in scenes:
            kf = seg.keyframe_path
            if kf and Path(kf).exists():
                vision = analyze_keyframe(kf)
                all_keywords.extend(vision.get("vision_tags", []))
                scene_dicts.append({
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "vision_tags": vision,
                })
            else:
                scene_dicts.append({
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "vision_tags": {},
                })

        unique_keywords = list(dict.fromkeys(all_keywords))[:10]

        # ── 3단계: 광고 에셋 생성 ────────────────────────────────
        img_result = generate_image_ad(unique_keywords)
        vid_result = generate_video_ad(unique_keywords)

        with engine.begin() as conn:
            # 이미지 광고 에셋 저장
            img_uid = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO TB_FAST_AD_ASSET
                        (ASSET_UID, VOD_ASSET_ID, AD_TYPE, GEN_PROMPT, SOURCE_KEYWORDS,
                         FILE_PATH, FILE_SIZE_BYTES, WIDTH_PX, HEIGHT_PX, GEN_API_PROVIDER, GEN_API_MODEL, STATUS)
                    VALUES (:uid, :vod, 'IMAGE', :prompt, :kw::jsonb, :fp, :fs, :w, :h, :prov, :model, 'GENERATED')
                """),
                {
                    "uid": img_uid, "vod": asset_id,
                    "prompt": img_result.get("prompt"),
                    "kw": json.dumps(unique_keywords),
                    "fp": img_result["file_path"],
                    "fs": img_result.get("file_size_bytes"),
                    "w": img_result.get("width_px"), "h": img_result.get("height_px"),
                    "prov": img_result.get("provider"), "model": img_result.get("model"),
                },
            )

            # 비디오 광고 에셋 저장
            vid_uid = str(uuid.uuid4())
            conn.execute(
                text("""
                    INSERT INTO TB_FAST_AD_ASSET
                        (ASSET_UID, VOD_ASSET_ID, AD_TYPE, GEN_PROMPT, SOURCE_KEYWORDS,
                         FILE_PATH, FILE_SIZE_BYTES, DURATION_SEC, WIDTH_PX, HEIGHT_PX, GEN_API_PROVIDER, GEN_API_MODEL, STATUS)
                    VALUES (:uid, :vod, 'VIDEO_SILENT', :prompt, :kw::jsonb, :fp, :fs, :dur, :w, :h, :prov, :model, 'GENERATED')
                """),
                {
                    "uid": vid_uid, "vod": asset_id,
                    "prompt": vid_result.get("prompt"),
                    "kw": json.dumps(unique_keywords),
                    "fp": vid_result["file_path"],
                    "fs": vid_result.get("file_size_bytes"),
                    "dur": vid_result.get("duration_sec", 4.0),
                    "w": vid_result.get("width_px"), "h": vid_result.get("height_px"),
                    "prov": vid_result.get("provider"), "model": vid_result.get("model"),
                },
            )

        # ── 4단계: 삽입 타임스탬프 계산 ──────────────────────────
        insertion_points = calculate_insertion_points(
            [{"start_time": s["start_time"], "end_time": s["end_time"]} for s in scene_dicts]
        )

        with engine.begin() as conn:
            for point in insertion_points:
                # 이미지 광고 타임스탬프
                conn.execute(
                    text("""
                        INSERT INTO TB_FAST_AD_INSERTION_POINT
                            (ID, VOD_ASSET_ID, AD_ASSET_UID, TIMESTAMP_SEC, CONFIDENCE,
                             INSERT_REASON, MOTION_SCORE, DISPLAY_DURATION_SEC, DISPLAY_POSITION)
                        VALUES (gen_random_uuid(), :vod, :uid, :ts, :conf, :reason, :motion, 4.0, 'OVERLAY_BOTTOM')
                    """),
                    {
                        "vod": asset_id, "uid": img_uid,
                        "ts": point["timestamp_sec"],
                        "conf": point["confidence"],
                        "reason": point["insert_reason"],
                        "motion": point["motion_score"],
                    },
                )

            # ── 파이프라인 상태: COMPLETED ─────────────────────────
            conn.execute(
                text("UPDATE TB_WEEKLY_FREE_VOD SET AD_PIPELINE_STATUS = 'COMPLETED', UPDATED_AT = NOW() WHERE WEEK_START_YMD = :w AND ASSET_ID = :aid"),
                {"w": week_start, "aid": asset_id},
            )

        log.info("pipeline.completed", asset_id=asset_id, insertion_points=len(insertion_points))

    except Exception as e:
        log.error("pipeline.failed", asset_id=asset_id, error=str(e))
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE TB_WEEKLY_FREE_VOD SET AD_PIPELINE_STATUS = 'FAILED', UPDATED_AT = NOW() WHERE WEEK_START_YMD = :w AND ASSET_ID = :aid"),
                {"w": week_start, "aid": asset_id},
            )
        raise


def weekly_batch_job():
    """주 1회 배치 잡 — 금주 무료 VOD 선정 + FAST 광고 파이프라인 실행."""
    log.info("weekly_batch.start")
    vods = select_weekly_free_vod()

    # 슬롯 미달 경고 (v2: 정상 결과는 10개여야 함)
    if len(vods) < WEEKLY_FREE_VOD_COUNT:
        log.warning(
            "weekly_vod.slot_shortage",
            selected=len(vods),
            expected=WEEKLY_FREE_VOD_COUNT,
        )

    for vod in vods:
        try:
            run_fast_ad_pipeline(vod)
        except Exception as e:
            log.error("batch.vod_failed", asset_id=vod.get("ASSET_ID"), error=str(e))
    log.info("weekly_batch.done", processed=len(vods))


if __name__ == "__main__":
    # cron 파싱: "분 시 일 월 요일"
    cron_parts = AD_BATCH_CRON.split()
    if len(cron_parts) == 5:
        minute, hour, day, month, day_of_week = cron_parts
    else:
        minute, hour, day_of_week = "0", "2", "mon"
        day, month = "*", "*"

    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        weekly_batch_job,
        "cron",
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        id="weekly_fast_ad_batch",
    )

    log.info("ad_batch.scheduler_started", cron=AD_BATCH_CRON)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("ad_batch.scheduler_stopped")
