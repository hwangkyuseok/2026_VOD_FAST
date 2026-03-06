# 📺 금주의 무료 VOD 10개 — 선정 기준 및 전체 구조 분석

> **분석일**: 2026-03-04  
> **관련 파일**: `ad-batch/app/main.py`, `backend-api/app/models/vod.py`, `backend-api/app/api/v1/vod.py`, `docs/schema_additions.sql`

---

## 1. 한눈에 보는 전체 흐름

```
매주 월요일 새벽 2시 (자동 실행)
        │
        ▼
[STEP 1] 선정 쿼리 실행
    TB_VOD_META에서 유료 VOD(IS_FREE_YN='N') 대상
    → selection_score 계산 후 상위 10개 추출
        │
        ▼
[STEP 2] TB_WEEKLY_FREE_VOD에 저장
    선정된 10개 VOD를 rank 1~10으로 기록
    + TB_VOD_META의 IS_FREE_YN='Y' 로 변경
        │
        ▼
[STEP 3] FAST 광고 파이프라인 실행 (VOD 10개 각각)
    씬 분할 → 비전 분석 → 광고 생성 → 타임스탬프 계산
        │
        ▼
[STEP 4] API 노출
    GET /api/v1/vod/weekly → 프론트엔드 "금주의 무료 VOD" 섹션
```

---

## 2. 선정 기준 — 핵심 점수 공식

> **파일**: `ad-batch/app/main.py` → `select_weekly_free_vod()` 함수 (43번째 줄)

```sql
SELECT ASSET_ID, TITLE, GENRE,
       COALESCE(VIEW_COUNT, 0) * 0.5 +
       COALESCE(RATING, 0) * 100 AS selection_score
FROM TB_VOD_META
WHERE IS_FREE_YN = 'N'          -- 유료 VOD 중에서만 선정
ORDER BY selection_score DESC
LIMIT 10                        -- 상위 10개
```

### 점수 공식 해석

| 요소 | 계산식 | 가중치 | 의미 |
|---|---|---|---|
| **조회수** | `VIEW_COUNT × 0.5` | 50% | 최근 인기도 반영 |
| **평점** | `RATING × 100` | 100배 | 콘텐츠 품질 반영 |

**예시 계산:**
```
VOD A: 조회수 5,000회, 평점 8.5점
  → 5000 × 0.5 + 8.5 × 100 = 2500 + 850 = 3,350점

VOD B: 조회수 3,000회, 평점 9.2점
  → 3000 × 0.5 + 9.2 × 100 = 1500 + 920 = 2,420점

→ VOD A가 더 높은 점수로 우선 선정됨
```

> **핵심 조건**: 반드시 **유료 VOD**(`IS_FREE_YN = 'N'`) 중에서만 선정.  
> 원래 유료인 콘텐츠를 이번 주에만 무료로 개방하는 방식.

---

## 3. 어디에 저장되는가 — 관련 테이블 구조

### 3.1 TB_WEEKLY_FREE_VOD (핵심 테이블)

> **파일**: `docs/schema_additions.sql` 133번째 줄 / `backend-api/app/models/vod.py` 50번째 줄

```
TB_WEEKLY_FREE_VOD
────────────────────────────────────────────────────────
컬럼명                | 타입          | 설명
────────────────────────────────────────────────────────
ID (PK)              | UUID          | 레코드 고유 ID (자동 생성)
WEEK_START_YMD       | VARCHAR(8)    | 해당 주 월요일 (예: "20260302")
ASSET_ID             | VARCHAR(100)  | VOD 고유 ID (TB_VOD_META 참조)
RANK_NO              | INTEGER       | 선정 순위 (1~10, 중복 불가)
SELECTION_SCORE      | NUMERIC(10,4) | 선정 점수 (조회수×0.5 + 평점×100)
SELECTION_REASON     | VARCHAR(100)  | 선정 사유 코드 (현재: "TREND_SCORE")
AD_PIPELINE_STATUS   | VARCHAR(20)   | 광고 파이프라인 상태
                     |               | PENDING → IN_PROGRESS → COMPLETED/FAILED
IS_ACTIVE            | CHAR(1)       | 활성 여부 (Y/N)
CREATED_AT           | TIMESTAMPTZ   | 생성 시각 (자동)
UPDATED_AT           | TIMESTAMPTZ   | 수정 시각 (자동)
────────────────────────────────────────────────────────
```

**DB 제약 조건:**
- `UNIQUE(WEEK_START_YMD, ASSET_ID)` — 같은 주에 같은 VOD 중복 불가
- `UNIQUE(WEEK_START_YMD, RANK_NO)` — 같은 주에 같은 순위 중복 불가
- `CHECK (RANK_NO >= 1 AND RANK_NO <= 10)` — 순위는 반드시 1~10

---

### 3.2 연관 테이블 관계도

```
TB_VOD_META (VOD 마스터)
  │  asset_id (PK)
  │  IS_FREE_YN = 'N' → 유료 (선정 전)
  │  IS_FREE_YN = 'Y' → 무료 (선정 후 변경)
  │  FAST_AD_ELIGIBLE_YN = 'Y' → 광고 삽입 대상
  │
  ├──► TB_WEEKLY_FREE_VOD (금주 선정 목록)
  │      week_start_ymd + rank_no 로 이번 주 순위 관리
  │
  └──► TB_FAST_AD_ASSET (광고 에셋)
         생성형 AI로 만든 이미지/무음비디오 광고
           │
           └──► TB_FAST_AD_INSERTION_POINT (삽입 타임스탬프)
                  VOD 재생 중 광고 오버레이 시점
```

---

## 4. 실행 시점 — 언제 선정되는가

> **파일**: `ad-batch/app/main.py` 29번째 줄 / 262번째 줄

```python
# 환경변수 (기본값)
AD_BATCH_CRON = "0 2 * * 1"       # 매주 월요일 새벽 2:00
WEEKLY_FREE_VOD_COUNT = 10         # 선정 개수 (기본: 10)
```

**cron 표현식 해석: `0 2 * * 1`**

| 필드 | 값 | 의미 |
|---|---|---| 
| 분 | `0` | 0분 |
| 시 | `2` | 새벽 2시 |
| 일 | `*` | 매일 중 |
| 월 | `*` | 매월 |
| 요일 | `1` | 월요일 |

→ **매주 월요일 새벽 02:00 (Asia/Seoul 기준)** 자동 실행

**설정 변경 방법**: 환경변수로 오버라이드 가능
```env
AD_BATCH_CRON=0 3 * * 1        # 새벽 3시로 변경
WEEKLY_FREE_VOD_COUNT=5        # 10개 대신 5개만 선정
```

---

## 5. 선정 후 처리 과정 (FAST 광고 파이프라인)

> **파일**: `ad-batch/app/main.py` → `run_fast_ad_pipeline()` 함수 (98번째 줄)

선정된 VOD 10개 각각에 대해 아래 4단계 파이프라인이 순차 실행됩니다.

```
1단계: 씬 분할 (PySceneDetect)
  └─ VOD 파일을 씬 단위로 자동 분할
  └─ 각 씬의 키프레임 이미지 추출

2단계: 비전 분석 (YOLO)
  └─ 키프레임에서 객체/키워드 태그 추출 (vision_tags)
  └─ 상위 10개 키워드 선별

3단계: 생성형 AI 광고 에셋 생성
  └─ 이미지 광고 (IMAGE): 키워드 기반 배너 이미지 생성
  └─ 무음 비디오 광고 (VIDEO_SILENT): 3~5초 무음 광고 영상 생성
  └─ TB_FAST_AD_ASSET에 저장

4단계: 광고 삽입 타임스탬프 계산
  └─ 저움직임 구간 감지 → 이탈율 최소화 최적 시점 선택
  └─ TB_FAST_AD_INSERTION_POINT에 저장
  └─ 클라이언트 플레이어가 이 데이터를 참조해 오버레이 표시
```

**파이프라인 상태 추적:**

```
PENDING → IN_PROGRESS → COMPLETED
                      → FAILED (예외 발생 시)
```

---

## 6. API 노출 — 프론트엔드에서 어떻게 읽는가

> **파일**: `backend-api/app/api/v1/vod.py` → `get_weekly_free_vod()` (51번째 줄)

```
GET /api/v1/vod/weekly
GET /api/v1/vod/weekly?week=20260302  (특정 주 조회)
```

**API 응답 구조 (WeeklyVodOut):**
```json
[
  {
    "rank_no": 1,
    "asset_id": "VOD_00123",
    "week_start_ymd": "20260302",
    "selection_score": 3350.0,
    "selection_reason": "TREND_SCORE",
    "ad_pipeline_status": "COMPLETED",
    "title": "드라마 타이틀",
    "genre": "드라마",
    "thumbnail_url": "https://...",
    "duration_sec": 3600
  },
  ...
]
```

**조회 조건:**
- `week_start_ymd = 현재 주 월요일`
- `is_active = 'Y'` (활성 상태만)
- `rank_no` 오름차순 정렬 (1위 → 10위)

---

## 7. 갱신 방식 — 매주 어떻게 교체되는가

`select_weekly_free_vod()` 내부에서 다음 순서로 안전하게 교체됩니다.

```python
# 1. 이전 주 VOD 비활성화
UPDATE TB_WEEKLY_FREE_VOD
SET IS_ACTIVE = 'N', UPDATED_AT = NOW()
WHERE WEEK_START_YMD = :현재주

# 2. 신규 선정 VOD 삽입 (Upsert 방식)
INSERT INTO TB_WEEKLY_FREE_VOD ...
ON CONFLICT (WEEK_START_YMD, ASSET_ID) DO UPDATE SET ...
-- 같은 주에 같은 VOD가 있으면 UPDATE, 없으면 INSERT

# 3. TB_VOD_META 상태 변경
UPDATE TB_VOD_META
SET IS_FREE_YN = 'Y', FAST_AD_ELIGIBLE_YN = 'Y'
WHERE ASSET_ID = :선정된_vod
```

> **주의**: 이전 주에 무료였던 VOD의 `IS_FREE_YN`을 다시 `'N'`으로 되돌리는 로직은  
> 현재 코드에 **명시적으로 없음**. 이전 무료 상태가 그대로 유지될 수 있음.

---

## 8. 설정 파일 위치 요약

| 항목 | 파일 | 위치 |
|---|---|---|
| 선정 점수 공식 | `ad-batch/app/main.py` | `select_weekly_free_vod()` L43 |
| 실행 스케줄 (cron) | `ad-batch/app/main.py` | `AD_BATCH_CRON` 환경변수 L29 |
| 선정 개수 | `ad-batch/app/main.py` | `WEEKLY_FREE_VOD_COUNT` 환경변수 L30 |
| DB 테이블 정의 | `docs/schema_additions.sql` | L136~171 |
| Python ORM 모델 | `backend-api/app/models/vod.py` | `WeeklyFreeVod` 클래스 L50 |
| API 엔드포인트 | `backend-api/app/api/v1/vod.py` | `get_weekly_free_vod()` L51 |

---

*분석 완료 — 관련 파일 6개, 선정 기준 1개 (조회수 × 0.5 + 평점 × 100)*
