# D-05. 상세 설계서 (Detailed Design)

> **문서 정보**

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 2026_TV — 차세대 미디어 플랫폼 |
| 문서 번호 | D-05 |
| 문서 버전 | v1.0 |
| 작성일 | 2026-03-04 |
| 작성자 | 개발팀 |

---

## 1. 클래스 다이어그램

### 1.1 backend-api ORM 모델

```mermaid
classDiagram
    class Base {
        <<SQLAlchemy DeclarativeBase>>
    }

    class VodMeta {
        +str asset_id PK
        +str|None title
        +str|None genre
        +str|None description
        +str|None hash_tag
        +str|None smry
        +str|None thumbnail_url
        +int|None duration_sec
        +str|None release_dt
        +float|None rating
        +int|None view_count
        +str is_free_yn
        +str fast_ad_eligible_yn
        +datetime|None nlp_vector_updated_at
        +str|None ttl
        +int|None use_fl
        +int|None svc_apy_fl
        +int|None thmbnl_fl
        +str|None disp_rtm
        +int|None is_hot_fl
        +str|None screen_tp
        +int|None epsd_no
        +str|None super_asset_nm
        +int|None rlse_year
    }

    class WeeklyFreeVod {
        +UUID id PK
        +str week_start_ymd
        +str asset_id FK
        +int rank_no
        +float|None selection_score
        +str|None selection_reason
        +str ad_pipeline_status
        +UUID|None ad_job_id
        +str is_active
        +datetime created_at
        +datetime updated_at
    }

    class VodNlpVector {
        +str asset_id PK FK
        +str|None source_text
        +list tfidf_vector
        +list keybert_keywords
        +str|None genre_code
        +str is_kids_genre
        +str|None model_version
    }

    class ChannelConfig {
        +int channel_no PK
        +str channel_nm
        +str category
        +str|None stream_url
        +str|None logo_url
        +str|None current_asset_id
        +str channel_color
        +str is_active
        +int sort_order
    }

    class WatchSession {
        +UUID session_id PK
        +str user_id
        +str session_type
        +int|None channel_no
        +str|None asset_id
        +datetime start_dt
        +datetime|None end_dt
        +int|None watch_sec
        +int ad_impression_count
        +int shopping_click_count
    }

    class FastAdAsset {
        +UUID asset_uid PK
        +str vod_asset_id FK
        +str ad_type
        +str|None gen_prompt
        +list source_keywords
        +str file_path
        +str status
    }

    class FastAdInsertionPoint {
        +UUID id PK
        +str vod_asset_id FK
        +UUID ad_asset_uid FK
        +float timestamp_sec
        +float confidence
        +str|None insert_reason
        +float|None motion_score
        +float display_duration_sec
        +str display_position
        +str is_active
    }

    Base <|-- VodMeta
    Base <|-- WeeklyFreeVod
    Base <|-- VodNlpVector
    Base <|-- ChannelConfig
    Base <|-- WatchSession
    Base <|-- FastAdAsset
    Base <|-- FastAdInsertionPoint

    VodMeta "1" --> "0..*" WeeklyFreeVod : asset_id
    VodMeta "1" --> "0..1" VodNlpVector : asset_id (CASCADE DELETE)
    VodMeta "1" --> "0..*" FastAdAsset : asset_id
    VodMeta "1" --> "0..*" FastAdInsertionPoint : asset_id
    FastAdAsset "1" --> "0..*" FastAdInsertionPoint : asset_uid (CASCADE DELETE)
```

---

### 1.2 ad-batch 모듈 구조

```mermaid
classDiagram
    class SceneSegment {
        +int scene_no
        +float start_time
        +float end_time
        +int start_frame
        +int end_frame
        +str|None keyframe_path
    }

    class SeasonalThemes {
        +dict SEASONAL_THEMES$
        +dict SLOT_REASON_MAP$
        +build_seasonal_case_when() str$
    }

    class AdBatchMain {
        +_current_week_start() str
        +_restore_previous_free_vod(conn, week) None
        +select_weekly_free_vod() List~Dict~
        +run_fast_ad_pipeline(vod) None
        +weekly_batch_job() None
    }

    class SceneDetector {
        +detect_scenes(video_path, work_dir) List~SceneSegment~
    }

    class VisionAnalyzer {
        +analyze_keyframe(keyframe_path) Dict
        -_run_yolo(img_path) List~str~
        -_run_clip(img_path) List~str~
        -_extract_colors(img_path) List~str~
    }

    class AdGenerator {
        +generate_image_ad(keywords) Dict
        +generate_video_ad(keywords) Dict
        -_keywords_to_prompt(keywords) str
        -_dalle3_generate(prompt) Dict
        -_pil_placeholder(keywords) Dict
    }

    class TimestampCalculator {
        +calculate_insertion_points(scenes) List~Dict~
        -_calc_motion_score(scene, max_duration) float
    }

    AdBatchMain --> SceneDetector : uses
    AdBatchMain --> VisionAnalyzer : uses
    AdBatchMain --> AdGenerator : uses
    AdBatchMain --> TimestampCalculator : uses
    AdBatchMain --> SeasonalThemes : imports
    SceneDetector --> SceneSegment : creates
```

---

## 2. 시퀀스 다이어그램

### 2.1 채널 Zapping 시퀀스

```mermaid
sequenceDiagram
    actor User as 사용자
    participant FE as Frontend
    participant Cache as Redis
    participant BE as backend-api
    participant DB as PostgreSQL

    User->>FE: ▲/▼ 키 입력
    activate FE
    FE->>BE: PATCH /api/v1/sessions/{id}/end
    BE->>DB: TB_WATCH_SESSION UPDATE end_dt, watch_sec
    DB-->>BE: OK
    BE-->>FE: SessionOut

    FE->>BE: GET /api/v1/channels/{newNo}
    BE->>Cache: GET channel:{newNo}
    alt 캐시 히트
        Cache-->>BE: ChannelConfig JSON
    else 캐시 미스
        BE->>DB: SELECT * FROM TB_CHANNEL_CONFIG WHERE channel_no=?
        DB-->>BE: ChannelConfig row
        BE->>Cache: SET channel:{newNo} EX 3600
        Cache-->>BE: OK
    end
    BE-->>FE: ChannelOut (stream_url 포함)

    FE->>FE: HLS.js.loadSource(stream_url)
    FE->>BE: POST /api/v1/sessions/start
    BE->>DB: TB_WATCH_SESSION INSERT
    DB-->>BE: SessionOut
    BE-->>FE: SessionOut
    deactivate FE
    Note over User,FE: 목표: 전체 500ms 이내
```

---

### 2.2 금주 VOD 선정 배치 시퀀스 (v2)

```mermaid
sequenceDiagram
    participant CRON as APScheduler
    participant MAIN as main.py
    participant DB as PostgreSQL
    participant SCENE as scene_detector
    participant VISION as vision_analyzer
    participant GEN as ad_generator
    participant CALC as timestamp_calculator

    CRON->>MAIN: weekly_batch_job() 트리거 (매주 월 02:00)

    MAIN->>DB: UPDATE TB_VOD_META SET IS_FREE_YN='N' (이전 주 복원)
    DB-->>MAIN: OK

    MAIN->>DB: UPDATE TB_WEEKLY_FREE_VOD IS_ACTIVE='N'
    DB-->>MAIN: OK

    MAIN->>DB: 3-CTE 쿼리 실행 (filtered→dedup→ranked_slots)
    Note over DB: Hard Filter + Soft Score + 시리즈 중복제거 + 슬롯 배분
    DB-->>MAIN: List[VOD 10개] (slot_group 포함)

    alt 결과 < 10개
        MAIN->>MAIN: log.warning "weekly_vod.slot_shortage"
    end

    loop 각 VOD별
        MAIN->>DB: TB_WEEKLY_FREE_VOD upsert (SLOT_REASON_MAP 적용)
        DB-->>MAIN: OK
        MAIN->>DB: TB_VOD_META IS_FREE_YN='Y' UPDATE
        MAIN->>DB: AD_PIPELINE_STATUS='IN_PROGRESS'

        MAIN->>SCENE: detect_scenes(vod_path)
        SCENE-->>MAIN: List[SceneSegment]

        loop 각 씬별
            MAIN->>VISION: analyze_keyframe(keyframe_path)
            VISION-->>MAIN: {vision_tags: [...]}
        end

        MAIN->>GEN: generate_image_ad(keywords)
        GEN-->>MAIN: {file_path, prompt, model}
        MAIN->>GEN: generate_video_ad(keywords)
        GEN-->>MAIN: {file_path, duration_sec}

        MAIN->>DB: TB_FAST_AD_ASSET INSERT (IMAGE + VIDEO_SILENT)
        DB-->>MAIN: OK

        MAIN->>CALC: calculate_insertion_points(scenes)
        CALC-->>MAIN: List[{timestamp_sec, confidence, insert_reason}]

        MAIN->>DB: TB_FAST_AD_INSERTION_POINT INSERT (최대 5개)
        MAIN->>DB: AD_PIPELINE_STATUS='COMPLETED'
    end
```

---

### 2.3 NLP 개인화 추천 시퀀스

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant NLP as nlp-api
    participant DB as PostgreSQL

    FE->>NLP: POST /admin/recommend {user_id, top_n:10}
    NLP->>DB: SELECT profile_vector, kids_boost_score<br/>FROM TB_USER_PROFILE_VECTOR WHERE user_id=?
    DB-->>NLP: row (or None)

    alt 프로필 벡터 있음
        NLP->>DB: SELECT tfidf_vector, is_kids_genre<br/>FROM TB_VOD_NLP_VECTOR JOIN TB_VOD_META WHERE is_free_yn='Y'
        DB-->>NLP: VOD 벡터 목록
        NLP->>NLP: cosine_similarity(user_vector, vod_vectors)
        NLP->>NLP: kids_boost_score 가중치 추가 (is_kids_genre='Y'인 경우)
        NLP->>NLP: 유사도 내림차순 정렬 → top_n 선정
        NLP->>NLP: 추천 사유 텍스트 생성 (score 범위별 분류)
    else 프로필 벡터 없음 + 시청 이력 있음
        NLP->>DB: SELECT asset, use_tms FROM TB_VOD_LOG WHERE user_id=?
        DB-->>NLP: 시청 이력
        NLP->>NLP: 시청 시간 기반 가중치 계산 (min(use_tms/3600, 1.0))
        NLP->>NLP: 가중 평균 벡터 계산 → 임시 프로필 생성
        Note over NLP: 위의 코사인 유사도 계산으로 진행
    else 완전 신규 유저 (Cold Start)
        NLP->>DB: SELECT asset_id, ttl, genre, thmbnl_pt<br/>FROM TB_VOD_META WHERE is_free_yn='Y'<br/>ORDER BY COALESCE(rate, 0) DESC LIMIT 10
        DB-->>NLP: 인기 VOD 목록
        NLP-->>FE: score=1.0, reason="인기 콘텐츠 추천 (시청 이력 없음)"
    end

    NLP-->>FE: RecommendResult[] 반환
```

---

### 2.4 FAST 광고 오버레이 재생 시퀀스

```mermaid
sequenceDiagram
    participant U as 사용자
    participant FE as Frontend
    participant BE as backend-api
    participant DB as PostgreSQL

    U->>FE: 트랙1 VOD 선택 (Enter)
    FE->>BE: GET /api/v1/ad/insertion-points/{asset_id}?min_confidence=0.5
    BE->>DB: SELECT timestamp_sec, confidence, display_duration_sec,<br/>file_path, ad_type FROM TB_FAST_AD_INSERTION_POINT<br/>JOIN TB_FAST_AD_ASSET WHERE is_active='Y'
    DB-->>BE: 삽입 포인트 목록 (최대 5개)
    BE-->>FE: InsertionPoint[]

    FE->>FE: 비디오 플레이어에 타임스탬프 배열 등록
    FE->>FE: VOD 영상 재생 시작

    loop 재생 중 (1초마다 체크)
        FE->>FE: currentTime 이 timestamp_sec와 일치?
        alt 일치 AND 해당 타임스탬프 미노출
            FE->>FE: AdOverlay 활성화 (display_position: OVERLAY_BOTTOM)
            FE->>FE: 4초 후 AdOverlay 자동 숨김
            FE->>FE: 해당 타임스탬프 노출 완료로 마킹 (중복 방지)
        end
    end

    U->>FE: ESC 키
    FE->>FE: 전체화면 플레이어 종료, /vod로 복귀
```

---

## 3. 모듈별 처리 로직

### 3.1 `select_weekly_free_vod()` 소프트 점수 계산 알고리즘

```
total_score =
    IS_HOT_FL 점수:    CASE WHEN IS_HOT_FL = 1 THEN 15 ELSE 0 END
  + 화질 점수:         CASE WHEN SCREEN_TP IN ('HD','FHD','UHD') THEN 10 ELSE 0 END
  + 키즈 1화 점수:     CASE WHEN (GENRE LIKE '%키즈%' OR GENRE LIKE '%애니%')
                            AND EPSD_NO = 1 THEN 15 ELSE 0 END
  + 4060 키워드 점수:  CASE WHEN SMRY ~ '(건강|자연인|고향|밥상|다큐|트로트)' THEN 20 ELSE 0 END
  + 시즌 테마 점수:    (seasonal_themes.py → build_seasonal_case_when() 생성)
                       CASE WHEN 현재월 AND 키워드 매칭 THEN 30 ELSE 0 END
```

**최대 가능 점수**: 15 + 10 + 15 + 20 + 30 = **90점**

### 3.2 `calculate_insertion_points()` 알고리즘

```python
# timestamp_calculator.py 핵심 로직
max_duration = max(씬길이 목록)
for 씬 in 씬목록:
    scene_duration = 씬.end_time - 씬.start_time
    motion_score = 1.0 - (scene_duration / max_duration)  # 짧을수록 고움직임
    confidence = 1.0 - motion_score  # 낮은 움직임 = 높은 신뢰도
    timestamp = 씬.start_time + 1.0  # 씬 시작 +1초

# 신뢰도(confidence) 내림차순 정렬 → 상위 5개 선정
# insert_reason 분류:
#   confidence >= 0.8 → "LOW_MOTION"
#   confidence >= 0.5 → "SCENE_BREAK"
#   otherwise         → "QUIET_MOMENT"
```

### 3.3 `build_seasonal_case_when()` 동적 SQL 생성

```python
# seasonal_themes.py
# SEASONAL_THEMES 딕셔너리에서 월별 SQL 자동 생성
for month, keywords in SEASONAL_THEMES.items():
    pattern = "|".join(keywords)  # 예: "추석|명절|가을|단풍|풍성한"
    # WHEN EXTRACT(MONTH FROM CURRENT_DATE) = 9
    #      AND (SMRY ~ '(추석|명절|가을|단풍|풍성한)' OR TTL ~ '(추석|명절|가을)') THEN 30
```

### 3.4 유저 프로필 벡터 생성 (`update_user_profile`)

```
1. TB_VOD_LOG에서 user_id 시청 이력 조회
2. 각 VOD별 가중치 계산:
   watch_weight = min(use_tms / 3600, 1.0)  # 최대 1시간 = 1.0
3. TB_VOD_NLP_VECTOR에서 해당 VOD의 tfidf_vector 조회
4. 가중 평균 벡터 계산:
   profile_vector = Σ(watch_weight × tfidf_vector) / Σ(watch_weight)
5. 키즈 비율 계산:
   kids_ratio = 키즈 시청 시간 / 전체 시청 시간
   kids_boost_score = max(0.1, min(1.0, 0.3 + kids_ratio * 0.7))
6. TB_USER_PROFILE_VECTOR UPSERT
```

---

## 4. 에러 처리 전략

| 에러 유형 | 처리 방법 | 로그 레벨 |
|---------|---------|---------|
| DB 연결 실패 | `pool_pre_ping=True` — 자동 재연결 시도 | ERROR |
| VOD 파일 없음 | 더미 씬 1개로 계속 진행 | WARNING |
| AI API 키 없음 | PIL 플레이스홀더 / ffmpeg 검은화면으로 fallback | WARNING |
| CLIP 로드 실패 | YOLO만으로 계속 진행 | WARNING |
| 슬롯 미달 | 경고 로그 출력 후 선정된 수만큼 진행 | WARNING |
| 파이프라인 실패 | `AD_PIPELINE_STATUS='FAILED'` 기록 + 다음 VOD 계속 | ERROR |
| Redis 연결 실패 | DB 직접 조회로 fallback (캐시 없이 동작) | ERROR |

---

## 5. 환경별 동작 차이

| 환경 | CLIP | AI API | VOD 파일 | 동작 |
|------|------|--------|---------|------|
| 개발 (CPU) | `CLIP_ENABLED=false` | 키 없음 | 없음 | YOLO만 사용, PIL 플레이스홀더, 더미 씬 |
| 스테이징 (GPU) | `CLIP_ENABLED=true` | 테스트 키 | 일부 존재 | 정상 동작 |
| 운영 (GPU) | `CLIP_ENABLED=true` | 실제 키 | 존재 | 전체 파이프라인 |
