# Changelog — 2026_TV 차세대 미디어 플랫폼

> 모든 아키텍처 설계, 코드 작성, DB 스키마 변경, 의사결정 사항은 이 파일에 날짜와 함께 기록합니다.
> 형식: `## [YYYY-MM-DD] 작업 제목`

---

## [2026-03-03] 0번 채널 (TV Commerce) 통합 구현

### 작업 내용

2026_TV_COMMERCE 프로젝트의 UI/UX를 2026_TV의 **CH 0 — HV 쇼핑TV** 채널로 통합.

#### 채널 내비게이션 변경
- `frontend/app/channel/page.tsx` 수정
  - `VIRTUAL_CH0` 가상 채널 객체 추가 (channel_no=0, category=SHOPPING)
  - `allChannels = [VIRTUAL_CH0, ...dbChannels]` 구성으로 채널 배열 재편성
  - 초기 진입 채널을 인덱스 1 (CH1)로 설정 (이전: 인덱스 0)
  - CH0 진입 시 `ChannelPlayer` 대신 `CommerceChannel` 렌더링
  - 채널 가이드 오버레이에 0번 채널 항목 추가
  - `handleChannelChange` 래퍼: CH1 ▼ → CH0, CH0 ▼ → CH30(마지막) 순환

#### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend-api/app/api/v1/commerce.py` | `GET /api/v1/commerce/data` — 메뉴·추천채널·상품 응답 (TB_PROD_INFO 실시간 조회) |
| `frontend/hooks/useRemoteFocus.ts` | TV 리모컨 방향키 포커스 훅 (2026_TV_COMMERCE 재사용) |
| `frontend/components/CommerceChannel/index.tsx` | 0번 채널 메인 레이아웃 (Sidebar+VideoPlayer+ShoppingRow) |
| `frontend/components/CommerceChannel/Sidebar.tsx` | CH0 전용 사이드바 (TV 메뉴, 시계) |
| `frontend/components/CommerceChannel/VideoPlayer.tsx` | 추천 채널 그라디언트 플레이어 |
| `frontend/components/CommerceChannel/ShoppingRow.tsx` | 하단 상품 카드 목록 (스크롤, 포커스) |
| `frontend/components/CommerceChannel/PurchaseModal.tsx` | 바로 구매 모달 (가격 < 20만원) |
| `frontend/components/CommerceChannel/ConsultModal.tsx` | 상담원 연결 모달 (가격 ≥ 20만원, 전화번호 입력) |

#### 수정 파일

| 파일 | 변경 사항 |
|------|----------|
| `backend-api/app/main.py` | `commerce` 라우터 등록 |
| `frontend/lib/api.ts` | `api.commerce.data()` 및 관련 타입 추가 |
| `frontend/tailwind.config.ts` | `tv-focus(#00e676)`, `tv-panel`, `tv-card` 컬러 추가 |
| `frontend/app/globals.css` | `.tv-focused` 포커스 링 유틸리티 클래스 추가 |

#### 0번 채널 주요 기능
- **리모컨 방향키 내비게이션**: ↑↓ (존 전환/메뉴), ←→ (채널/상품 이동), Enter (상품 선택)
- **B키**: 사이드바 토글 (TV 리모컨 Back/메뉴 버튼)
- **결제 분기**: 상품 가격 < 20만원 → 바로구매 모달 / ≥ 20만원 → 상담연결 모달
- **포커스 트랩**: 모달 열림 시 방향키 포커스가 모달 내부에만 한정
- **상품 데이터**: `TB_PROD_INFO`에서 실시간 조회 (fallback: 빈 상태 안내 화면)

---

## [2026-03-03] 로그 파일 관리 시스템 도입

### 작업 내용
- **backend-api**: `app/core/logging.py` 신규 생성
  - loguru `setup_logging()` 함수 — 콘솔 핸들러 + 파일 핸들러 통합
  - uvicorn / SQLAlchemy stdlib logging → loguru 리디렉션 (`_InterceptHandler`)
  - `app.log` (10 MB 회전, 7일 보관) / `error.log` (ERROR+, 30일 보관) 분리
  - `app/core/config.py`에 `log_dir: str = "/app/logs"` 추가
  - `app/main.py`에 `setup_logging()` 호출 추가 (앱 객체 생성 이전)

- **nlp-api**: 동일 구조로 `app/core/logging.py` 신규 생성 및 `main.py` 연동

- **ad-batch**: `app/logging_setup.py` 신규 생성
  - structlog 유지, stdlib `RotatingFileHandler`를 통해 파일 출력 연동
  - `structlog.stdlib.ProcessorFormatter`로 파일 포맷 통일
  - `app.log` (10 MB 회전, 7개 백업) / `error.log` (ERROR+, 30개 백업)
  - `app/main.py`에 `setup_logging()` 호출 추가

- **frontend**: `lib/logger.ts` 신규 생성
  - pino 기반 서버사이드 로거 (API Route / Server Component 전용)
  - 개발 환경: pino-pretty 컬러 콘솔 출력
  - 프로덕션: `multistream` — 콘솔 + `app.log` + `error.log` 동시 기록
  - `package.json`에 `pino@^9.6.0`, `pino-pretty@^13.0.0` 추가

- **docker-compose.yml**: 각 서비스에 호스트 바인드 마운트 추가
  ```
  ./logs/backend-api  → /app/logs  (backend-api)
  ./logs/nlp-api      → /app/logs  (nlp-api)
  ./logs/ad-batch     → /app/logs  (ad-batch)
  ./logs/frontend     → /app/logs  (frontend)
  ```
- **.env.example**: `LOG_DIR=/app/logs` 항목 추가

### 로그 파일 구조
```
logs/
├── backend-api/
│   ├── app.log       (INFO+, 10 MB 회전, 7일 보관, zip 압축)
│   └── error.log     (ERROR+, 10 MB 회전, 30일 보관)
├── nlp-api/
│   ├── app.log
│   └── error.log
├── ad-batch/
│   ├── app.log       (INFO+, 10 MB 회전, 최대 7개 백업)
│   └── error.log     (ERROR+, 최대 30개 백업)
└── frontend/
    ├── app.log       (pino JSON, 프로덕션만)
    └── error.log     (ERROR+, 프로덕션만)
```

---

## [2026-03-02] 프로젝트 초기 설계 및 셋업

### 작업 내용

#### 1. 참조 프로젝트 분석 완료

**2026_TV_COMMERCE** (`D:\20.WORKSPACE\2026_TV_COMMERCE`) 분석:
- 기술 스택: FastAPI(Python) + Next.js(TypeScript) + PostgreSQL + APScheduler
- 외부 PostgreSQL 연결 패턴 확인 (DATABASE_URL 환경변수 주입)
- docker-compose: backend + frontend 2컨테이너, 외부 DB 미포함 구성
- 핵심 DB 스키마 추출:
  - `TB_CUST_INFO`: 고객 약정서비스 현황 (AGE_GRP10, KIDS_USE_PV_MONTH1 등 주요 컬럼 포함)
  - `TB_VOD_LOG`: 고객별 VOD 시청이력 (GENRE_OF_CT_CL, USE_TMS 등)
  - `TB_VOD_META`: VOD 콘텐츠 상세 마스터 (GENRE, HASH_TAG, DESCRIPTION 등 NLP 활용 가능)
  - `TB_PROD_INFO`: 쇼핑 상품 정보 (PLATFORM, SALE_PRICE, THUMBNAIL_URL 등)

**2026_ADWARE** (`D:\20.WORKSPACE\2026_ADWARE`) 분석:
- 기술 스택: FastAPI 멀티 마이크로서비스 + Redis 큐 + PostgreSQL + Docker
- 서비스 구성: api-gateway, preprocessor, analyzer, insertion-detector, output-service
- 핵심 패턴:
  - `PySceneDetect ContentDetector` 기반 씬 분할 (`scene_detector.py`)
  - `SQLAlchemy async engine` + `asyncpg` DB 연결 패턴 (`shared/utils/db.py`)
  - YOLO 비전 분석 패턴 (`services/analyzer/vision.py`)
- 핵심 DB 스키마 추출:
  - `jobs`: 배치 작업 상태 관리 (UUID, status, video_path)
  - `scene_analyses`: 씬 분석 결과 (vision_tags JSONB, start_time, end_time)
  - `insertion_points`: 광고 삽입 시점 (timestamp, confidence, context_tags JSONB)

#### 2. 아키텍처 설계 결정

**컨테이너 구성 (4개 신규 + Redis)**:
| 컨테이너 | 포트 | 역할 |
|----------|------|------|
| `frontend` | 3000 | Next.js 셋탑박스 에뮬레이터 UI |
| `backend-api` | 8000 | FastAPI 메인 API (고객/VOD/채널/쇼핑) |
| `nlp-api` | 8001 | NLP 추천 API (`/admin/vod_proc`) |
| `ad-batch` | - | FAST 광고 생성 배치 워커 |
| `redis` | 6379 | 배치 작업 큐 + 캐시 |
| PostgreSQL | 5432 | **외부 운영 중** (컨테이너 미포함) |

**핵심 설계 의사결정**:
- PostgreSQL은 `YOUR_SERVER_IP:5432/YOUR_DB_NAME`에 이미 운영 중 → docker-compose에서 DB 컨테이너 제외
- FAST 광고는 원본 영상 수정 없이 클라이언트 플레이어 오버레이 방식 채택 (비침습적)
- 씬 분할은 오디오 완전 배제, 비디오 프레임 기반(PySceneDetect)만 사용
- 키즈·애니메이션 강제 포함: `TB_USER_PROFILE_VECTOR.kids_boost_score` 컬럼으로 구현

#### 3. 생성된 파일 목록

| 파일 | 설명 |
|------|------|
| `claude.md` | AI 컨텍스트 문서 (프로젝트 마스터 기획) |
| `changelog.md` | 작업 이력 관리 파일 (이 파일) |
| `.env.example` | 환경변수 템플릿 |
| `docs/architecture.md` | 상세 아키텍처 설계 문서 |
| `docs/schema_additions.sql` | 신규 테이블 DDL (기존 테이블 확장 포함) |

#### 4. DB 스키마 설계

**기존 테이블 재사용** (스키마 변경 없음):
- `TB_CUST_INFO`, `TB_VOD_LOG`, `TB_VOD_META`, `TB_PROD_INFO` (2026_TV_COMMERCE)
- `jobs`, `scene_analyses`, `insertion_points` (2026_ADWARE)

**기존 테이블 컬럼 추가**:
- `TB_VOD_META`: `IS_FREE_YN CHAR(1)`, `FAST_AD_ELIGIBLE_YN CHAR(1)`, `NLP_VECTOR_UPDATED_AT TIMESTAMPTZ`

**신규 테이블**:
- `TB_USER_PROFILE_VECTOR`: 유저 NLP 프로필 벡터 + kids_boost_score
- `TB_VOD_NLP_VECTOR`: VOD별 TF-IDF/KeyBERT 벡터 캐시
- `TB_WEEKLY_FREE_VOD`: 금주의 무료 VOD (트랙 1, 주간 배치)
- `TB_CHANNEL_CONFIG`: 가상 채널 30개 구성
- `TB_WATCH_SESSION`: 채널/VOD 시청 세션 로그
- `TB_FAST_AD_ASSET`: FAST 광고 에셋 (이미지/영상 메타데이터)
- `TB_FAST_AD_INSERTION_POINT`: VOD별 광고 삽입 최적 타임스탬프 캐시

---

## [2026-03-02] 전체 서비스 초기 구현 완료

### 작업 내용

#### 1. 인프라 파일 생성

| 파일 | 내용 |
|------|------|
| `.gitignore` | Python/.env/Node.js/모델 파일 제외 |
| `docker-compose.yml` | 4서비스 + Redis 오케스트레이션 (외부 PostgreSQL 미포함) |

#### 2. backend-api (FastAPI, Port 8000)

- `Dockerfile` + `requirements.txt`
- `app/core/config.py` — pydantic-settings 기반 환경변수 관리
- `app/core/db.py` — SQLAlchemy async engine (asyncpg)
- `app/models/` — ChannelConfig, VodMeta, VodNlpVector, WeeklyFreeVod, WatchSession, FastAdAsset, FastAdInsertionPoint, UserProfileVector
- `app/api/v1/channels.py` — 채널 목록/상세/스트림 업데이트
- `app/api/v1/vod.py` — 금주 무료 VOD, 무료 VOD 목록, 상세 조회
- `app/api/v1/customers.py` — 고객 정보 조회
- `app/api/v1/shopping.py` — 키워드 기반 상품 매칭, 상품 목록
- `app/api/v1/sessions.py` — 시청 세션 시작/종료
- `app/api/v1/ad.py` — 광고 삽입 타임스탬프 조회

#### 3. nlp-api (FastAPI, Port 8001)

- `Dockerfile` + `requirements.txt` (scikit-learn, KeyBERT, sentence-transformers)
- `app/vectorizer.py` — TF-IDF + KeyBERT 벡터화, 키즈 장르 판별
- `app/recommender.py` — 코사인 유사도 + kids_boost_score 가중치 추천
- `app/api/vod_proc.py` — `/admin/vod_proc`, `/admin/recommend`, `/admin/update_user_profile`

#### 4. ad-batch (Python APScheduler)

- `Dockerfile` + `requirements.txt` (scenedetect, ultralytics, ffmpeg-python, openai)
- `app/scene_detector.py` — PySceneDetect ContentDetector (오디오 배제 재확인)
- `app/vision_analyzer.py` — YOLO 객체 감지 + 색상 추출
- `app/ad_generator.py` — 생성형 AI 이미지/무음 비디오 광고 생성 (API 없을 시 플레이스홀더)
- `app/timestamp_calculator.py` — 저움직임 구간 기반 광고 삽입 타임스탬프 계산
- `app/main.py` — APScheduler 주 1회 배치 파이프라인

#### 5. frontend (Next.js 14 App Router)

- `Dockerfile` (multi-stage 빌드, standalone output)
- `tailwind.config.ts` — TV 전용 컬러 팔레트 (tv-bg, tv-primary, tv-kids 등)
- `app/page.tsx` — 부팅 화면 (2.5초 후 자동 전환)
- `app/setup/page.tsx` — 초기 프로필 설정 (2단계: ID → 프로필)
- `app/channel/page.tsx` — 채널 플레이어 화면 (채널 가이드 포함)
- `app/vod/page.tsx` — VOD 목록 (트랙1/트랙2 탭, 인라인 플레이어)
- `components/ChannelPlayer/` — Up/Down Zapping + 키보드 제어
- `components/AdOverlay/` — 타임스탬프 기반 FAST 광고 오버레이
- `components/ShoppingOverlay/` — 30초마다 키워드 기반 쇼핑 매칭
- `lib/api.ts` — Backend API + NLP API 클라이언트

#### 6. DB 스키마 수정 (docs/schema_additions.sql)

- `update_updated_at()` 공통 트리거 함수 추가 (누락된 함수 보완)

#### 7. 버그 수정

- `nlp-api/app/api/vod_proc.py`: Python `str()` → `json.dumps()` (None→null 직렬화 버그)
- `backend-api/app/models/channel.py`: 미사용 import 제거
- `backend-api/app/models/vod.py`: 미사용 `Dict` 타입 제거

### 테스트 결과

- Python 구문 검사 (py_compile): 24개 파일 전체 통과

---

<!-- 이후 작업 내역은 아래에 동일한 형식으로 추가 -->

