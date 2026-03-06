# 📋 금주 무료 VOD 큐레이션 v2 — 구현 계획서

> **작성일**: 2026-03-04  
> **상태**: 🔴 미착수 (실제 코드 변경 전 검토용)  
> **변경 범위**: `ad-batch/app/main.py` (핵심), `backend-api/app/models/vod.py` (ORM 보완)

---

## 1. 현재(v1) vs 목표(v2) 비교

| 항목 | 현재 v1 | 목표 v2 |
|---|---|---|
| **선정 기준** | 조회수×0.5 + 평점×100 (단순 수식) | 3단계 필터 + 슬롯 배분 + 시즌 보너스 |
| **슬롯 구조** | 없음 (단순 상위 10개) | 키즈3 + 교양/다큐4 + 예능2 + 기타1 |
| **하드 필터** | IS_FREE_YN='N' 조건만 | USE_FL, THMBNL_FL, DISP_RTM 20분+ |
| **소프트 점수** | 없음 | IS_HOT_FL, SCREEN_TP, 4060 키워드 |
| **시리즈** | 고려 없음 | 시리즈당 1개 + 키즈 1화 우선 |
| **시즌 보너스** | 없음 | 월별 테마 키워드 +30점 |
| **중복 제거** | 없음 | SUPER_ASSET_NM 기준 중복 제거 |

---

## 2. 컬럼 매핑 확인 (TB_VOD_META DDL 검증 완료)

새 전략에서 사용하는 컬럼들이 실제 `TB_VOD_META`에 존재하는지 확인합니다.

| 전략에서 사용하는 컬럼 | DDL 실제 컬럼 | 타입 | 확인 |
|---|---|---|---|
| `use_fl` | `USE_FL` | INTEGER (0/1) | ✅ 존재 |
| `svc_apy_fl` | `SVC_APY_FL` | INTEGER | ✅ 존재 |
| `thmbnl_fl` | `THMBNL_FL` | INTEGER (0/1) | ✅ 존재 |
| `disp_rtm` | `DISP_RTM` | VARCHAR(20) ⚠️ | ✅ 존재, **문자열 주의** |
| `is_hot_fl` | `IS_HOT_FL` | INTEGER (0/1) | ✅ 존재 |
| `screen_tp` | `SCREEN_TP` | VARCHAR(50) | ✅ 존재 |
| `smry` | `SMRY` | TEXT | ✅ 존재 |
| `ttl` | `TTL` | VARCHAR(255) | ✅ 존재 |
| `genre` | `GENRE` | VARCHAR(100) | ✅ 존재 |
| `epsd_no` | `EPSD_NO` | INTEGER | ✅ 존재 |
| `super_asset_nm` | `SUPER_ASSET_NM` | VARCHAR(255) | ✅ 존재 |
| `rlse_year` | `RLSE_YEAR` | INTEGER | ✅ 존재 |

> ⚠️ **`DISP_RTM` 타입 주의**: DDL에서 `VARCHAR(20)`으로 정의됨 (`"00:20:00"` 형식의 문자열).  
> SQL에서 `>= '00:20:00'` 문자열 비교로도 동작하지만, 정확한 비교를 위해 아래 검증 후 처리 필요.

---

## 3. 구현 작업 목록 (체크리스트)

### STEP 1. `ad-batch/app/main.py` — `select_weekly_free_vod()` 함수 교체

- [ ] **기존 단순 쿼리 제거**
  ```python
  # 제거 대상 (현재 코드 L47~58)
  SELECT ASSET_ID, TITLE, GENRE,
         COALESCE(VIEW_COUNT, 0) * 0.5 + COALESCE(RATING, 0) * 100 AS selection_score
  FROM TB_VOD_META WHERE IS_FREE_YN = 'N' ORDER BY selection_score DESC LIMIT :count
  ```

- [ ] **새 CTE 쿼리로 교체** (아래 §4 쿼리 참조)

- [ ] **반환 딕셔너리 키 매핑 확인**  
  기존: `vod["ASSET_ID"]` 사용 → 새 쿼리도 동일 키 반환하도록 SELECT 절 유지

- [ ] **슬롯 부족 시 폴백 로직 추가**  
  예) 키즈 VOD가 3개 미만이면 ETC 슬롯에서 보충하거나 경고 로그 출력

---

### STEP 2. `backend-api/app/models/vod.py` — `VodMeta` 모델 컬럼 추가

현재 `VodMeta` 클래스에는 새 쿼리에서 필요한 원본 컬럼들이 누락되어 있습니다.

- [ ] 아래 컬럼 추가 (SQLAlchemy ORM 기준)
  ```python
  # 추가 필요 컬럼 (backend-api/app/models/vod.py)
  ttl: Mapped[str | None] = mapped_column(String(255), nullable=True)       # 제목 (TTL)
  use_fl: Mapped[int | None] = mapped_column(Integer, nullable=True)         # 사용여부
  svc_apy_fl: Mapped[int | None] = mapped_column(Integer, nullable=True)    # 서비스플래그
  thmbnl_fl: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 썸네일여부
  disp_rtm: Mapped[str | None] = mapped_column(String(20), nullable=True)   # 상영시간
  is_hot_fl: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 인기작여부
  screen_tp: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 화질타입
  smry: Mapped[str | None] = mapped_column(Text, nullable=True)             # 줄거리
  epsd_no: Mapped[int | None] = mapped_column(Integer, nullable=True)       # 회차번호
  super_asset_nm: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 상위에셋명
  rlse_year: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 출시년도
  ```
  > 참고: `TITLE`, `GENRE`는 이미 `title`, `genre`로 존재하지만 DDL 원본명은 `TTL`, `GENRE` 이므로  
  > 배치 쿼리가 raw SQL이라 ORM 수정과 무관하게 작동함. ORM은 API용.

---

### STEP 3. `ad-batch/app/main.py` — 월별 테마 딕셔너리 외부화 (선택)

- [ ] 현재 SQL 내 CASE-WHEN 하드코딩된 월별 테마를 환경변수 또는 별도 설정 파일로 분리 (선택사항)
  ```python
  # 예: ad-batch/app/seasonal_themes.py 신규 생성
  SEASONAL_THEMES = {
      1:  ["겨울", "설날", "새해", "연말"],
      3:  ["봄", "벚꽃", "입학", "새학기"],
      5:  ["어린이", "가족", "효도", "엄마", "아빠", "사랑"],
      8:  ["여름", "바다", "휴가", "피서"],
      9:  ["추석", "명절", "가을", "단풍", "풍성한"],
      12: ["크리스마스", "연말", "겨울", "산타"],
  }
  ```

---

### STEP 4. `TB_WEEKLY_FREE_VOD` — `SELECTION_REASON` 값 확장

- [ ] 현재 코드는 `SELECTION_REASON = 'TREND_SCORE'` 고정
- [ ] 새 전략에 맞게 슬롯 구분 정보 기록 (저장만, DB 스키마 변경 불필요)
  ```python
  # 예시 값
  'TREND_SCORE'  → 기존 (폐기 예정)
  'SLOT_KIDS'    → 키즈/애니 슬롯
  'SLOT_DOCU'    → 교양/다큐 슬롯
  'SLOT_ENT'     → 예능/음악 슬롯
  'SLOT_ETC'     → 기타/명품 슬롯
  ```

---

## 4. 신규 선정 쿼리 (교체 대상)

> 아래 쿼리를 `select_weekly_free_vod()` 함수 내 `text(...)` 블록으로 적용합니다.

```sql
WITH filtered_data AS (
    SELECT 
        ASSET_ID,
        TTL,
        EPSD_NM,
        GENRE,
        -- 1. 기본 가점 (인기작, 고화질)
        (CASE WHEN IS_HOT_FL = 1 THEN 15 ELSE 0 END) +
        (CASE WHEN SCREEN_TP IN ('HD', 'FHD', 'UHD') THEN 10 ELSE 0 END) +
        
        -- 2. 키즈 정주행 유도 가점 (키즈/애니 장르 + 1화)
        (CASE WHEN (GENRE LIKE '%키즈%' OR GENRE LIKE '%애니%') AND EPSD_NO = 1 THEN 15 ELSE 0 END) +
        
        -- 3. 4060 타겟 키워드 가점 (PostgreSQL 정규표현식)
        (CASE WHEN SMRY ~ '(건강|자연인|고향|밥상|다큐|트로트)' THEN 20 ELSE 0 END) +
        
        -- 4. 월별 테마 가점 (현재 월 자동 감지)
        (CASE 
            WHEN EXTRACT(MONTH FROM CURRENT_DATE) = 5 
                 AND (SMRY ~ '(어린이|가족|효도|엄마|아빠|사랑)' OR TTL ~ '(어린이|가족|효도)') THEN 30
            WHEN EXTRACT(MONTH FROM CURRENT_DATE) = 9 
                 AND (SMRY ~ '(추석|명절|가을|단풍|풍성한)' OR TTL ~ '(추석|명절|가을)') THEN 30
            ELSE 0 
        END) AS total_score,
        
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
      AND IS_FREE_YN = 'N'          -- 유료 VOD에서만 선정
      AND DISP_RTM >= '00:20:00'    -- 20분 미만 자투리 제외
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
    total_score DESC;
```

---

## 5. ⚠️ 주의사항 및 리스크

### 5-1. DISP_RTM 문자열 비교

`DISP_RTM`은 `VARCHAR(20)` 타입으로 `"01:30:00"` 형식의 문자열입니다.  
`>= '00:20:00'` 비교는 **사전순 문자열 비교**로 동작하여 대부분의 경우 정상 작동하지만,  
형식이 불일치한 데이터(예: `"120"`, `"1:20"`)가 있으면 오작동할 수 있습니다.

**사전 검증 쿼리:**
```sql
-- 형식 이상 데이터 확인
SELECT DISP_RTM, COUNT(*)
FROM TB_VOD_META
WHERE DISP_RTM !~ '^\d{2}:\d{2}:\d{2}$'
  AND DISP_RTM IS NOT NULL
GROUP BY DISP_RTM ORDER BY COUNT(*) DESC LIMIT 20;
```

### 5-2. 슬롯 미달 시나리오

키즈 VOD가 3편 미만이거나, DOCU_LIFE가 4편 미만일 수 있습니다.  
`weekly_batch_job()`에서 선정 결과가 10개 미만이면 **경고 로그를 명시적으로 출력**하는 코드를 추가해야 합니다.

```python
# 추가 권장 코드 (ad-batch/app/main.py weekly_batch_job 내부)
if len(vods) < WEEKLY_FREE_VOD_COUNT:
    log.warning("weekly_vod.slot_shortage", selected=len(vods), expected=WEEKLY_FREE_VOD_COUNT)
```

### 5-3. 기존 IS_FREE_YN 복원 미처리 (기존 v1 버그 인계)

이전 주에 무료로 변경된 VOD의 `IS_FREE_YN`을 `'N'`으로 되돌리는 로직이 없습니다.  
v2 구현 시 함께 해결을 검토하세요.

```sql
-- 이전 주 무료 VOD 복원 (개선 방향)
UPDATE TB_VOD_META m
SET IS_FREE_YN = 'N', FAST_AD_ELIGIBLE_YN = 'N'
WHERE m.ASSET_ID IN (
    SELECT ASSET_ID FROM TB_WEEKLY_FREE_VOD
    WHERE WEEK_START_YMD < :current_week AND IS_ACTIVE = 'N'
)
AND m.ASSET_ID NOT IN (
    SELECT ASSET_ID FROM TB_WEEKLY_FREE_VOD
    WHERE WEEK_START_YMD = :current_week AND IS_ACTIVE = 'Y'
);
```

---

## 6. 월별 테마 전체 가이드 (12개월)

아래 테마는 SQL CASE-WHEN 절을 확장하여 적용합니다.

| 월 | 테마 | 키워드 예시 (SMRY/TTL 검색) |
|---|---|---|
| 1월 | 새해/겨울 | 새해, 겨울, 설날, 신년 |
| 2월 | 설 연휴 | 설날, 명절, 가족, 한복 |
| 3월 | 봄/입학 | 봄, 벚꽃, 새학기, 입학 |
| 4월 | 봄 여행 | 여행, 봄, 꽃구경, 나들이 |
| 5월 | 가정의 달 | 어린이, 가족, 효도, 엄마, 아빠 |
| 6월 | 스포츠/여름 | 여름, 축구, 스포츠, 야구 |
| 7월 | 여름 휴가 | 여름, 바다, 휴가, 피서 |
| 8월 | 광복절/여름 | 독립, 광복, 역사, 바다 |
| 9월 | 추석/가을 | 추석, 명절, 가을, 단풍, 풍성한 |
| 10월 | 가을/할로윈 | 가을, 단풍, 공포, 미스터리 |
| 11월 | 수능/가을 | 청춘, 학교, 도전, 가을 |
| 12월 | 연말/크리스마스 | 크리스마스, 연말, 겨울, 산타 |

---

## 7. 수행 순서 요약

```
[사전] 1. DISP_RTM 형식 검증 쿼리 실행 → 이상 데이터 확인
       2. 새 쿼리를 DB에서 직접 테스트 실행 → 결과 10건 확인

[개발] 3. ad-batch/app/main.py — select_weekly_free_vod() 쿼리 교체
       4. SELECTION_REASON 슬롯별 코드 적용
       5. 슬롯 미달 경고 로그 추가
       6. (선택) backend-api/app/models/vod.py ORM 컬럼 추가

[검증] 7. ad-batch 컨테이너 수동 실행 → TB_WEEKLY_FREE_VOD 결과 확인
          python -m app.main (또는 weekly_batch_job() 직접 호출)
       8. GET /api/v1/vod/weekly API 응답 확인
       9. 프론트엔드 "금주의 무료 VOD" 섹션 렌더링 확인

[선택] 10. IS_FREE_YN 복원 로직 추가 (v1 버그 해결)
       11. 월별 테마 12개월 전체 CASE-WHEN 확장
```

---

*이 문서는 실제 코드 적용 전 검토용입니다. 작업 착수 전 §5 주의사항을 반드시 확인하세요.*
