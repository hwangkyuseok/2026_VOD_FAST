-- ============================================================
-- 2026_TV — 신규 테이블 DDL 및 기존 테이블 확장
-- PostgreSQL 16
-- DB: hv02 @ YOUR_SERVER_IP:5432
--
-- 실행 전 확인사항:
--   1. 기존 테이블 (TB_CUST_INFO, TB_VOD_LOG, TB_VOD_META, TB_PROD_INFO)은
--      이미 생성되어 있어야 합니다. (2026_TV_COMMERCE ddl.sql 참조)
--   2. 기존 테이블 (jobs, scene_analyses, insertion_points)은
--      이미 생성되어 있어야 합니다. (2026_ADWARE init.sql 참조)
-- ============================================================

-- uuid-ossp 확장 (없으면 설치)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- 벡터 확장 (pgvector 설치 필요 — NLP 벡터 저장용)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 공통 UPDATED_AT 자동 갱신 트리거 함수
-- (2026_TV_COMMERCE에 이미 존재하면 OR REPLACE로 덮어쓰기 무해)
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.UPDATED_AT = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 기존 테이블 컬럼 추가 (ALTER TABLE)
-- ============================================================

-- TB_VOD_META: FAST 광고 및 NLP 처리 관련 컬럼 추가
ALTER TABLE TB_VOD_META
    ADD COLUMN IF NOT EXISTS IS_FREE_YN          CHAR(1)     DEFAULT 'N',
    ADD COLUMN IF NOT EXISTS FAST_AD_ELIGIBLE_YN CHAR(1)     DEFAULT 'N',
    ADD COLUMN IF NOT EXISTS NLP_VECTOR_UPDATED_AT TIMESTAMPTZ;

COMMENT ON COLUMN TB_VOD_META.IS_FREE_YN IS '무료 콘텐츠 여부 (Y: 무료, N: 유료)';
COMMENT ON COLUMN TB_VOD_META.FAST_AD_ELIGIBLE_YN IS 'FAST 광고 파이프라인 적용 대상 여부 (트랙1 선정 시 Y)';
COMMENT ON COLUMN TB_VOD_META.NLP_VECTOR_UPDATED_AT IS 'NLP 벡터 마지막 갱신 일시';

CREATE INDEX IF NOT EXISTS IDX_VOD_META_FREE ON TB_VOD_META (IS_FREE_YN);
CREATE INDEX IF NOT EXISTS IDX_VOD_META_FAST_AD ON TB_VOD_META (FAST_AD_ELIGIBLE_YN);


-- ============================================================
-- 신규 테이블 1: 유저 NLP 프로필 벡터
-- NLP 추천 타겟팅용 유저 선호도 벡터 저장
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_USER_PROFILE_VECTOR (
    USER_ID             VARCHAR(20)     NOT NULL,
    -- 유저 선호 벡터 (JSON 배열 형태로 저장, pgvector 도입 전 호환)
    PROFILE_VECTOR      JSONB           NOT NULL DEFAULT '[]',
    -- 선호 장르 키워드 목록 (상위 N개)
    FAVORITE_GENRES     JSONB           NOT NULL DEFAULT '[]',
    -- 선호 키워드 (KeyBERT 추출 결과)
    FAVORITE_KEYWORDS   JSONB           NOT NULL DEFAULT '[]',
    -- 키즈·애니메이션 부스트 점수 (0.0 ~ 1.0)
    -- 절대 0으로 만들지 말 것: 비즈니스 룰상 키즈는 항상 추천 대상
    KIDS_BOOST_SCORE    NUMERIC(4,3)    NOT NULL DEFAULT 0.300
                        CHECK (KIDS_BOOST_SCORE >= 0.1 AND KIDS_BOOST_SCORE <= 1.0),
    -- 최근 시청 장르 상위 5개 (추천 사유 생성용)
    RECENT_GENRES       JSONB           NOT NULL DEFAULT '[]',
    -- 총 시청 시간 (초) — 프로필 신뢰도 판단용
    TOTAL_WATCH_SEC     BIGINT          NOT NULL DEFAULT 0,
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UPDATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT TB_USER_PROFILE_VECTOR_PK PRIMARY KEY (USER_ID)
);

COMMENT ON TABLE TB_USER_PROFILE_VECTOR IS '유저 NLP 추천 프로필 벡터 (개인화 추천 트랙2 전용)';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.USER_ID IS '고객ID (TB_CUST_INFO.USER_ID 참조)';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.PROFILE_VECTOR IS '유저 선호 벡터 (TF-IDF 공간 기준 JSONB 배열)';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.FAVORITE_GENRES IS '선호 장르 코드 목록 [{genre, score}]';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.FAVORITE_KEYWORDS IS '선호 키워드 [{keyword, weight}]';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.KIDS_BOOST_SCORE IS '키즈/애니 추천 가중치 (최소 0.1 보장 - 비즈니스 룰)';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.RECENT_GENRES IS '최근 30일 시청 장르 상위 5개';
COMMENT ON COLUMN TB_USER_PROFILE_VECTOR.TOTAL_WATCH_SEC IS '누적 시청 시간(초) - 프로필 신뢰도 판단';

CREATE OR REPLACE FUNCTION update_user_profile_vector_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.UPDATED_AT = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_profile_vector_updated_at
    BEFORE UPDATE ON TB_USER_PROFILE_VECTOR
    FOR EACH ROW EXECUTE FUNCTION update_user_profile_vector_updated_at();


-- ============================================================
-- 신규 테이블 2: VOD NLP 텍스트 벡터 캐시
-- TB_VOD_META의 텍스트 메타데이터를 벡터화하여 캐시
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_VOD_NLP_VECTOR (
    ASSET_ID            VARCHAR(100)    NOT NULL,
    -- 벡터화에 사용된 소스 텍스트 (DESCRIPTION + HASH_TAG + GENRE + SMRY 조합)
    SOURCE_TEXT         TEXT,
    -- TF-IDF 벡터 (JSONB 배열)
    TFIDF_VECTOR        JSONB           NOT NULL DEFAULT '[]',
    -- KeyBERT 추출 키워드 [{keyword, score}]
    KEYBERT_KEYWORDS    JSONB           NOT NULL DEFAULT '[]',
    -- 장르 코드 (빠른 키즈 필터링용 비정규화 컬럼)
    GENRE_CODE          VARCHAR(100),
    IS_KIDS_GENRE       CHAR(1)         NOT NULL DEFAULT 'N',
    -- 모델 버전 (재벡터화 필요 판단용)
    MODEL_VERSION       VARCHAR(50),
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UPDATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT TB_VOD_NLP_VECTOR_PK PRIMARY KEY (ASSET_ID),
    CONSTRAINT FK_VOD_NLP_VECTOR_META
        FOREIGN KEY (ASSET_ID) REFERENCES TB_VOD_META (ASSET_ID) ON DELETE CASCADE
);

COMMENT ON TABLE TB_VOD_NLP_VECTOR IS 'VOD 콘텐츠 NLP 벡터 캐시 (추천 엔진 성능 최적화)';
COMMENT ON COLUMN TB_VOD_NLP_VECTOR.ASSET_ID IS 'TB_VOD_META.ASSET_ID 참조';
COMMENT ON COLUMN TB_VOD_NLP_VECTOR.IS_KIDS_GENRE IS '키즈/애니메이션 장르 여부 (추천 시 가중치 적용 식별자)';
COMMENT ON COLUMN TB_VOD_NLP_VECTOR.MODEL_VERSION IS 'TF-IDF/KeyBERT 모델 버전 식별자';

CREATE INDEX IF NOT EXISTS IDX_VOD_NLP_VECTOR_KIDS ON TB_VOD_NLP_VECTOR (IS_KIDS_GENRE);
CREATE INDEX IF NOT EXISTS IDX_VOD_NLP_VECTOR_GENRE ON TB_VOD_NLP_VECTOR (GENRE_CODE);

CREATE TRIGGER trg_vod_nlp_vector_updated_at
    BEFORE UPDATE ON TB_VOD_NLP_VECTOR
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 신규 테이블 3: 금주의 무료 VOD (트랙 1)
-- 주 1회 배치로 선정, 전 고객 공통 적용, FAST 광고 삽입 대상
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_WEEKLY_FREE_VOD (
    ID                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- 해당 주의 시작일 (월요일 기준, YYYYMMDD)
    WEEK_START_YMD      VARCHAR(8)      NOT NULL,
    ASSET_ID            VARCHAR(100)    NOT NULL,
    -- 선정 순위 (1~10)
    RANK_NO             INTEGER         NOT NULL CHECK (RANK_NO >= 1 AND RANK_NO <= 10),
    -- 선정 기준 점수 (트렌드 + 조회수 + 평점 가중 합산)
    SELECTION_SCORE     NUMERIC(10,4),
    -- 선정 사유 코드 (TREND_SCORE, HOT_CONTENT, GLOBAL_POPULAR 등)
    SELECTION_REASON    VARCHAR(100),
    -- FAST 광고 파이프라인 처리 상태 (PENDING, IN_PROGRESS, COMPLETED, FAILED)
    AD_PIPELINE_STATUS  VARCHAR(20)     NOT NULL DEFAULT 'PENDING',
    -- 광고 배치 작업 ID (jobs 테이블 참조)
    AD_JOB_ID           UUID,
    IS_ACTIVE           CHAR(1)         NOT NULL DEFAULT 'Y',
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UPDATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT TB_WEEKLY_FREE_VOD_UKEY UNIQUE (WEEK_START_YMD, ASSET_ID),
    CONSTRAINT TB_WEEKLY_FREE_VOD_RANK UNIQUE (WEEK_START_YMD, RANK_NO),
    CONSTRAINT FK_WEEKLY_FREE_VOD_META
        FOREIGN KEY (ASSET_ID) REFERENCES TB_VOD_META (ASSET_ID),
    CONSTRAINT FK_WEEKLY_FREE_VOD_JOB
        FOREIGN KEY (AD_JOB_ID) REFERENCES jobs (id)
);

COMMENT ON TABLE TB_WEEKLY_FREE_VOD IS '금주의 무료 VOD 목록 (트랙1 - FAST 광고 삽입 대상, 전 고객 공통)';
COMMENT ON COLUMN TB_WEEKLY_FREE_VOD.WEEK_START_YMD IS '해당 주 시작일 (매주 월요일 YYYYMMDD)';
COMMENT ON COLUMN TB_WEEKLY_FREE_VOD.RANK_NO IS '금주 무료 VOD 선정 순위 (1~10)';
COMMENT ON COLUMN TB_WEEKLY_FREE_VOD.AD_PIPELINE_STATUS IS 'FAST 광고 파이프라인 처리 상태';

CREATE INDEX IF NOT EXISTS IDX_WEEKLY_FREE_VOD_WEEK ON TB_WEEKLY_FREE_VOD (WEEK_START_YMD, IS_ACTIVE);

CREATE TRIGGER trg_weekly_free_vod_updated_at
    BEFORE UPDATE ON TB_WEEKLY_FREE_VOD
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 신규 테이블 4: 가상 채널 구성 (30개)
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_CHANNEL_CONFIG (
    CHANNEL_NO          INTEGER         PRIMARY KEY CHECK (CHANNEL_NO >= 1 AND CHANNEL_NO <= 99),
    CHANNEL_NM          VARCHAR(100)    NOT NULL,
    -- 채널 카테고리 (NEWS, ENTERTAINMENT, KIDS, SHOPPING, SPORTS, MOVIE, DRAMA 등)
    CATEGORY            VARCHAR(50)     NOT NULL,
    -- HLS 스트림 URL 또는 VOD 플레이리스트 경로
    STREAM_URL          TEXT,
    -- 로고 이미지 경로
    LOGO_URL            TEXT,
    -- 현재 방송 중 콘텐츠 (TB_VOD_META.ASSET_ID 참조, nullable)
    CURRENT_ASSET_ID    VARCHAR(100),
    -- 채널 색상 (UI 렌더링용 HEX 코드)
    CHANNEL_COLOR       VARCHAR(7)      DEFAULT '#1a1a2e',
    IS_ACTIVE           CHAR(1)         NOT NULL DEFAULT 'Y',
    SORT_ORDER          INTEGER         NOT NULL DEFAULT 0,
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UPDATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE TB_CHANNEL_CONFIG IS '가상 채널 30개 구성 정보 (셋탑박스 에뮬레이터용)';
COMMENT ON COLUMN TB_CHANNEL_CONFIG.CHANNEL_NO IS '채널 번호 (1~99)';
COMMENT ON COLUMN TB_CHANNEL_CONFIG.CATEGORY IS '채널 카테고리 (KIDS 포함 필수)';
COMMENT ON COLUMN TB_CHANNEL_CONFIG.STREAM_URL IS 'HLS 스트림 URL (m3u8)';

CREATE INDEX IF NOT EXISTS IDX_CHANNEL_CONFIG_ACTIVE ON TB_CHANNEL_CONFIG (IS_ACTIVE, SORT_ORDER);

CREATE TRIGGER trg_channel_config_updated_at
    BEFORE UPDATE ON TB_CHANNEL_CONFIG
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 초기 채널 30개 시드 데이터
INSERT INTO TB_CHANNEL_CONFIG (CHANNEL_NO, CHANNEL_NM, CATEGORY, CHANNEL_COLOR, SORT_ORDER) VALUES
    (1,  'HV 뉴스',         'NEWS',          '#c0392b', 1),
    (2,  'HV 생활경제',      'NEWS',          '#e74c3c', 2),
    (3,  'HV 드라마',        'DRAMA',         '#8e44ad', 3),
    (4,  'HV 드라마2',       'DRAMA',         '#9b59b6', 4),
    (5,  'HV 영화',          'MOVIE',         '#2c3e50', 5),
    (6,  'HV 영화2',         'MOVIE',         '#34495e', 6),
    (7,  'HV 예능',          'ENTERTAINMENT', '#e67e22', 7),
    (8,  'HV 예능2',         'ENTERTAINMENT', '#f39c12', 8),
    (9,  'HV 키즈',          'KIDS',          '#27ae60', 9),
    (10, 'HV 애니',          'KIDS',          '#2ecc71', 10),
    (11, 'HV 스포츠',        'SPORTS',        '#2980b9', 11),
    (12, 'HV 스포츠2',       'SPORTS',        '#3498db', 12),
    (13, 'HV 쇼핑',          'SHOPPING',      '#d35400', 13),
    (14, 'HV 홈쇼핑2',       'SHOPPING',      '#e67e22', 14),
    (15, 'HV 음악',          'MUSIC',         '#1abc9c', 15),
    (16, 'HV 다큐',          'DOCUMENTARY',   '#16a085', 16),
    (17, 'HV 교육',          'EDUCATION',     '#2980b9', 17),
    (18, 'HV 키즈교육',      'KIDS',          '#27ae60', 18),
    (19, 'HV 오락',          'ENTERTAINMENT', '#f1c40f', 19),
    (20, 'HV 지역',          'LOCAL',         '#95a5a6', 20),
    (21, 'HV 골프',          'SPORTS',        '#27ae60', 21),
    (22, 'HV 바둑',          'LEISURE',       '#7f8c8d', 22),
    (23, 'HV 트로트',        'MUSIC',         '#e74c3c', 23),
    (24, 'HV 요리생활',      'LIFESTYLE',     '#f39c12', 24),
    (25, 'HV 패션뷰티',      'LIFESTYLE',     '#fd79a8', 25),
    (26, 'HV 여행',          'TRAVEL',        '#00b894', 26),
    (27, 'HV 자연다큐',      'DOCUMENTARY',   '#55efc4', 27),
    (28, 'HV 역사',          'DOCUMENTARY',   '#636e72', 28),
    (29, 'HV 공개방송',      'ENTERTAINMENT', '#fdcb6e', 29),
    (30, 'HV FAST+',         'FAST',          '#6c5ce7', 30)
ON CONFLICT (CHANNEL_NO) DO NOTHING;


-- ============================================================
-- 신규 테이블 5: 시청 세션 로그
-- 채널 및 VOD 시청 이력 (실시간 분석용, TB_VOD_LOG와 별도)
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_WATCH_SESSION (
    SESSION_ID          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    USER_ID             VARCHAR(20)     NOT NULL,
    -- 시청 유형 (CHANNEL: 실시간 채널, VOD_TRACK1: 금주 무료, VOD_TRACK2: 개인화)
    SESSION_TYPE        VARCHAR(20)     NOT NULL CHECK (SESSION_TYPE IN ('CHANNEL', 'VOD_TRACK1', 'VOD_TRACK2')),
    -- 채널 시청 시
    CHANNEL_NO          INTEGER,
    -- VOD 시청 시
    ASSET_ID            VARCHAR(100),
    -- 시청 시작/종료 일시
    START_DT            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    END_DT              TIMESTAMPTZ,
    -- 실제 시청 시간 (초) — END_DT - START_DT 자동 계산 또는 클라이언트 전송값
    WATCH_SEC           INTEGER,
    -- FAST 광고 노출 횟수 (트랙1 전용)
    AD_IMPRESSION_COUNT INTEGER         NOT NULL DEFAULT 0,
    -- 쇼핑 클릭 횟수
    SHOPPING_CLICK_COUNT INTEGER        NOT NULL DEFAULT 0,
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE TB_WATCH_SESSION IS '시청 세션 로그 (실시간 채널 + VOD 양방향, 유저 프로필 벡터 갱신용)';
COMMENT ON COLUMN TB_WATCH_SESSION.SESSION_TYPE IS '시청 유형: CHANNEL(실시간), VOD_TRACK1(금주무료), VOD_TRACK2(개인화)';
COMMENT ON COLUMN TB_WATCH_SESSION.AD_IMPRESSION_COUNT IS 'FAST 광고 오버레이 노출 횟수 (트랙1 전용)';

CREATE INDEX IF NOT EXISTS IDX_WATCH_SESSION_USER ON TB_WATCH_SESSION (USER_ID, START_DT DESC);
CREATE INDEX IF NOT EXISTS IDX_WATCH_SESSION_ASSET ON TB_WATCH_SESSION (ASSET_ID, START_DT DESC);
CREATE INDEX IF NOT EXISTS IDX_WATCH_SESSION_CHANNEL ON TB_WATCH_SESSION (CHANNEL_NO, START_DT DESC);


-- ============================================================
-- 신규 테이블 6: FAST 광고 에셋 메타데이터
-- 생성형 AI로 생성된 이미지/무음 비디오 광고 에셋 관리
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_FAST_AD_ASSET (
    ASSET_UID           UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- 연관 VOD (트랙1 금주 무료 VOD)
    VOD_ASSET_ID        VARCHAR(100)    NOT NULL,
    -- 씬 분석 결과 참조 (2026_ADWARE 재사용 테이블)
    SCENE_ANALYSIS_ID   UUID,
    -- 에셋 유형 (IMAGE: 이미지 팝업, VIDEO_SILENT: 무음 비디오)
    AD_TYPE             VARCHAR(20)     NOT NULL CHECK (AD_TYPE IN ('IMAGE', 'VIDEO_SILENT')),
    -- 생성형 AI에 사용된 프롬프트 텍스트
    GEN_PROMPT          TEXT,
    -- 원본 씬 키워드 (vision_tags에서 추출)
    SOURCE_KEYWORDS     JSONB           NOT NULL DEFAULT '[]',
    -- 생성된 파일 경로 (컨테이너 내부 경로)
    FILE_PATH           TEXT            NOT NULL,
    -- 파일 크기 (bytes)
    FILE_SIZE_BYTES     BIGINT,
    -- 영상 길이 (VIDEO_SILENT 전용, 초)
    DURATION_SEC        NUMERIC(6,2),
    -- 해상도
    WIDTH_PX            INTEGER,
    HEIGHT_PX           INTEGER,
    -- 생성 API 정보
    GEN_API_PROVIDER    VARCHAR(50),    -- 예: OPENAI, STABILITY, RUNWAY
    GEN_API_MODEL       VARCHAR(100),   -- 예: dall-e-3, stable-diffusion-xl
    -- 처리 상태 (GENERATED, APPROVED, REJECTED, EXPIRED)
    STATUS              VARCHAR(20)     NOT NULL DEFAULT 'GENERATED',
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UPDATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT FK_FAST_AD_ASSET_VOD
        FOREIGN KEY (VOD_ASSET_ID) REFERENCES TB_VOD_META (ASSET_ID),
    CONSTRAINT FK_FAST_AD_ASSET_SCENE
        FOREIGN KEY (SCENE_ANALYSIS_ID) REFERENCES scene_analyses (id) ON DELETE SET NULL
);

COMMENT ON TABLE TB_FAST_AD_ASSET IS 'FAST 광고 에셋 메타데이터 (생성형 AI 결과물 이미지/무음비디오)';
COMMENT ON COLUMN TB_FAST_AD_ASSET.AD_TYPE IS '광고 에셋 유형: IMAGE(이미지팝업), VIDEO_SILENT(무음숏폼)';
COMMENT ON COLUMN TB_FAST_AD_ASSET.DURATION_SEC IS '무음 비디오 길이 (목표: 3~5초)';
COMMENT ON COLUMN TB_FAST_AD_ASSET.STATUS IS '에셋 상태: GENERATED(생성완료), APPROVED(승인), REJECTED(반려), EXPIRED(만료)';

CREATE INDEX IF NOT EXISTS IDX_FAST_AD_ASSET_VOD ON TB_FAST_AD_ASSET (VOD_ASSET_ID, STATUS);
CREATE INDEX IF NOT EXISTS IDX_FAST_AD_ASSET_TYPE ON TB_FAST_AD_ASSET (AD_TYPE, STATUS);

CREATE TRIGGER trg_fast_ad_asset_updated_at
    BEFORE UPDATE ON TB_FAST_AD_ASSET
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ============================================================
-- 신규 테이블 7: FAST 광고 삽입 최적 타임스탬프 (캐시)
-- VOD 재생 시 클라이언트 플레이어가 참조하여 오버레이 타이밍 결정
-- ============================================================
CREATE TABLE IF NOT EXISTS TB_FAST_AD_INSERTION_POINT (
    ID                  UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- 대상 VOD
    VOD_ASSET_ID        VARCHAR(100)    NOT NULL,
    -- 연관 광고 에셋
    AD_ASSET_UID        UUID            NOT NULL,
    -- 광고 삽입 타임스탬프 (초, 소수점 3자리)
    TIMESTAMP_SEC       NUMERIC(10,3)   NOT NULL,
    -- 삽입 적합도 점수 (0.0 ~ 1.0, 높을수록 이탈율 낮은 최적 구간)
    CONFIDENCE          NUMERIC(4,3)    NOT NULL CHECK (CONFIDENCE >= 0 AND CONFIDENCE <= 1),
    -- 삽입 선정 사유 (LOW_MOTION: 저움직임, SCENE_BREAK: 씬전환후, QUIET_MOMENT: 조용한순간)
    INSERT_REASON       VARCHAR(50),
    -- 해당 구간의 광학 흐름 점수 (낮을수록 저움직임)
    MOTION_SCORE        NUMERIC(6,4),
    -- 광고 표시 지속 시간 (초, 이미지: 3~5초, 영상: AD_ASSET의 DURATION_SEC)
    DISPLAY_DURATION_SEC NUMERIC(6,2)   NOT NULL DEFAULT 4.0,
    -- 광고 표시 위치 (OVERLAY_BOTTOM: 하단오버레이, OVERLAY_FULLSCREEN: 전체화면)
    DISPLAY_POSITION    VARCHAR(30)     NOT NULL DEFAULT 'OVERLAY_BOTTOM',
    IS_ACTIVE           CHAR(1)         NOT NULL DEFAULT 'Y',
    CREATED_AT          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT FK_FAST_AD_INSERT_VOD
        FOREIGN KEY (VOD_ASSET_ID) REFERENCES TB_VOD_META (ASSET_ID),
    CONSTRAINT FK_FAST_AD_INSERT_ASSET
        FOREIGN KEY (AD_ASSET_UID) REFERENCES TB_FAST_AD_ASSET (ASSET_UID) ON DELETE CASCADE
);

COMMENT ON TABLE TB_FAST_AD_INSERTION_POINT IS 'FAST 광고 삽입 최적 타임스탬프 캐시 (클라이언트 플레이어 오버레이 기준)';
COMMENT ON COLUMN TB_FAST_AD_INSERTION_POINT.TIMESTAMP_SEC IS '광고 오버레이 시작 타임스탬프 (초)';
COMMENT ON COLUMN TB_FAST_AD_INSERTION_POINT.CONFIDENCE IS '삽입 적합도 (1.0 = 이탈율 최소 최적 구간)';
COMMENT ON COLUMN TB_FAST_AD_INSERTION_POINT.MOTION_SCORE IS '구간 광학흐름 점수 (낮을수록 저움직임 = 광고 적합)';
COMMENT ON COLUMN TB_FAST_AD_INSERTION_POINT.DISPLAY_POSITION IS '광고 표시 위치: OVERLAY_BOTTOM(하단), OVERLAY_FULLSCREEN(전체)';

CREATE INDEX IF NOT EXISTS IDX_FAST_AD_INSERT_VOD
    ON TB_FAST_AD_INSERTION_POINT (VOD_ASSET_ID, IS_ACTIVE, TIMESTAMP_SEC);
CREATE INDEX IF NOT EXISTS IDX_FAST_AD_INSERT_CONFIDENCE
    ON TB_FAST_AD_INSERTION_POINT (VOD_ASSET_ID, CONFIDENCE DESC);


-- ============================================================
-- 완료 메시지
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '2026_TV 신규 스키마 적용 완료';
    RAISE NOTICE '생성된 테이블: TB_USER_PROFILE_VECTOR, TB_VOD_NLP_VECTOR, TB_WEEKLY_FREE_VOD';
    RAISE NOTICE '             TB_CHANNEL_CONFIG (30채널 시드 포함), TB_WATCH_SESSION';
    RAISE NOTICE '             TB_FAST_AD_ASSET, TB_FAST_AD_INSERTION_POINT';
    RAISE NOTICE '수정된 테이블: TB_VOD_META (IS_FREE_YN, FAST_AD_ELIGIBLE_YN, NLP_VECTOR_UPDATED_AT 컬럼 추가)';
END;
$$;
