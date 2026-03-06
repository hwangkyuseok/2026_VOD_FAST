# 2026_TV — 프로젝트 마스터 기획 정의서

> **이 파일은 Claude(AI 에이전트)가 프로젝트 컨텍스트를 빠르게 파악하기 위한 핵심 참조 문서입니다.**
> 작업 이력·변경사항은 이 파일에 기록하지 않고 반드시 `changelog.md`에 기록합니다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | 2026_TV — 차세대 미디어 플랫폼 |
| **목표** | 케이블 TV 셋톱박스 방송 시스템을 Web App으로 에뮬레이션한 미디어 플랫폼 |
| **핵심 수익 모델** | FAST(Free Ad-supported Streaming TV) 광고 수익 + 실시간 쇼핑 커머스 |
| **작업 디렉토리** | `D:\20.WORKSPACE\2026_TV` |
| **타겟 서버 IP** | `YOUR_SERVER_IP` |

---

## 2. 인프라 접속 정보

> **중요:** 아래 정보는 `.env` 파일에서만 관리하며, 소스코드에 절대 하드코딩 금지.

```
# 타겟 배포 서버
SERVER_IP=YOUR_SERVER_IP
SSH_PORT=22
SSH_USER=YOUR_SSH_USER
# (SSH 패스워드는 .env에만 기록)

# 공통 PostgreSQL DB (외부 운영 중)
DB_HOST=YOUR_SERVER_IP
DB_PORT=5432
DB_NAME=YOUR_DB_NAME
DB_USER=YOUR_DB_USER
# (DB 패스워드는 .env에만 기록)
```

---

## 3. 핵심 비즈니스 룰 (절대 위반 금지)

> ⚠️ **추천·타겟팅 로직 설계의 최우선 제약사항**

- 전체 가입자의 90% 이상이 40대 이상이더라도, **키즈 및 애니메이션 콘텐츠의 실제 이용률이 매우 높음**.
- **어떠한 경우에도** 키즈·애니메이션 장르를 추천 풀이나 초기 타겟팅에서 **배제하지 말 것**.
- 키즈·애니메이션은 오히려 **주요 추천 요소**로 취급해야 함.
- VOD 추천 로직(`/admin/vod_proc`)에서 코사인 유사도 계산 시 키즈·애니메이션 장르에 대한 **별도 가중치(boost) 적용** 권장.

---

## 4. 주요 기능 명세

### A. 셋탑박스 에뮬레이션 Web App

- **초기 진입**: 전원 ON 시 사용자 프로필 설정 화면
- **실시간 채널**: 30개 가상 채널, 영상 스트리밍 + Up/Down Zapping
- **실시간 쇼핑 매칭**: 비전 AI로 화면 내 객체 인식 → 내부 쇼핑 DB 상품 매칭 → 하단/측면 UI 노출

### B. 투트랙(Two-Track) VOD 추천

| | 트랙 1: 금주의 무료 VOD | 트랙 2: 당신을 위한 무료 VOD |
|---|---|---|
| **대상** | 원래 유료 VOD 중 트렌드 상위 10개 | 기존 무료 VOD 풀에서 개인화 10개 |
| **적용 범위** | 전 고객 공통 | 고객 개별 |
| **광고** | FAST 광고 삽입 (C 파이프라인) | 광고 없음 |
| **갱신 주기** | 주 1회 Batch | 실시간/로그인 시 |

**NLP 추천 로직 (`/admin/vod_proc`)**:
1. `TF-IDF + KeyBERT`로 VOD 메타데이터 텍스트 벡터화
2. 고객 시청 이력(`TB_VOD_LOG`)으로 유저 프로필 벡터 생성
3. 코사인 유사도로 상위 10개 선정 (키즈·애니 가중치 적용)
4. 추천 사유 텍스트 생성 후 UI에 노출

### C. 생성형 AI 기반 FAST 광고 파이프라인 (주 1회 Batch)

```
1단계: 비디오 프레임 추출 → PySceneDetect (ContentDetector, 오디오 배제)
2단계: YOLO / SlowFast → 씬 내 객체·행동 키워드 추출 (vision_tags)
3단계: 키워드 → 생성형 AI 프롬프트 변환
        - 이미지: 고해상도 상품 썸네일/팝업 이미지 생성
        - 비디오: 무음(Silent) 3~5초 숏폼 영상 생성
4단계: 광고 삽입 최적 타임스탬프 계산 (저움직임 구간) → DB 캐싱
        → 클라이언트 플레이어에서 Overlay 방식으로 원본 수정 없이 노출
```

---

## 5. 시스템 아키텍처

### 5.1 컨테이너 구성 (Docker)

```
┌─────────────────────────────────────────────────────────┐
│                   YOUR_SERVER_IP 서버                    │
│                                                          │
│  ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │  frontend   │    │         backend-api              │  │
│  │  (Next.js)  │◄──►│    (FastAPI, Port 8000)         │  │
│  │  Port 3000  │    │  - 고객/VOD/채널/쇼핑 API        │  │
│  └─────────────┘    └────────────┬────────────────────┘  │
│                                  │                        │
│  ┌─────────────────┐    ┌────────┴──────────────────┐    │
│  │    nlp-api      │    │        ad-batch            │    │
│  │ (FastAPI, 8001) │    │  (Python Batch Worker)     │    │
│  │ - NLP 추천 엔진  │    │  - FAST 광고 생성 파이프라인 │    │
│  │ - /admin/vod_proc│   │  - 주 1회 스케줄 실행       │    │
│  └─────────────────┘   └────────────────────────────┘    │
│                                                          │
│  ┌─────────────┐                                          │
│  │    redis    │  ← 배치 작업 큐, 캐시                      │
│  │  Port 6379  │                                          │
│  └─────────────┘                                          │
│                                                          │
│  ━━━━━━━━━━━━━━━━━ 외부 DB (이미 운영 중) ━━━━━━━━━━━━━━━ │
│  PostgreSQL 16  @  YOUR_SERVER_IP:5432  /  YOUR_DB_NAME          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 기술 스택

| 레이어 | 기술 | 참조 프로젝트 |
|--------|------|--------------|
| **Frontend** | Next.js 14+ (App Router), TypeScript, Tailwind CSS | 2026_TV_COMMERCE |
| **Backend API** | FastAPI + SQLAlchemy(async) + Pydantic v2 | 2026_TV_COMMERCE + 2026_ADWARE |
| **NLP API** | FastAPI + scikit-learn + KeyBERT + sentence-transformers | 신규 |
| **Ad Batch** | Python + PySceneDetect + YOLO + ffmpeg-python | 2026_ADWARE |
| **DB** | PostgreSQL 16 (외부) | 공통 |
| **Queue/Cache** | Redis 7 | 2026_ADWARE |
| **스케줄러** | APScheduler 3.x | 2026_TV_COMMERCE |
| **로깅** | loguru (backend) / structlog (batch) | 2026_TV_COMMERCE + 2026_ADWARE |
| **컨테이너** | Docker + docker-compose | 공통 |

---

## 6. 데이터베이스 스키마

### 6.1 기존 테이블 (2026_TV_COMMERCE DDL에서 재사용)

| 테이블명 | 설명 |
|----------|------|
| `TB_CUST_INFO` | 고객 약정서비스 현황 및 이용내역 (PK: SHA2_HASH, USER_ID, P_MT) |
| `TB_VOD_LOG` | 고객별 VOD 시청이력 (PK: SRL_NO, P_MT) |
| `TB_VOD_META` | VOD 콘텐츠 상세 마스터 (PK: ASSET_ID) |
| `TB_PROD_INFO` | 쇼핑 상품 정보 (PK: SRL_NO, UNIQUE: PLATFORM+PROD_CD) |

### 6.2 재사용 테이블 (2026_ADWARE에서 재사용)

| 테이블명 | 설명 |
|----------|------|
| `jobs` | 배치 작업 상태 관리 (UUID PK) |
| `scene_analyses` | 씬 분석 결과 (vision_tags JSONB) |
| `insertion_points` | 광고 삽입 시점 (timestamp, confidence) |

### 6.3 신규 테이블 (본 프로젝트 추가)

전체 DDL: [`docs/schema_additions.sql`](docs/schema_additions.sql) 참조

| 테이블명 | 설명 |
|----------|------|
| `TB_USER_PROFILE_VECTOR` | 유저 NLP 프로필 벡터 (키즈 가중치 포함) |
| `TB_VOD_NLP_VECTOR` | VOD별 TF-IDF/KeyBERT 텍스트 벡터 |
| `TB_WEEKLY_FREE_VOD` | 금주의 무료 VOD (트랙 1, 주간 갱신) |
| `TB_CHANNEL_CONFIG` | 가상 채널 30개 구성 정보 |
| `TB_WATCH_SESSION` | 채널/VOD 시청 세션 로그 |
| `TB_FAST_AD_ASSET` | FAST 광고 에셋 메타데이터 (이미지/영상) |
| `TB_FAST_AD_INSERTION_POINT` | VOD별 광고 삽입 최적 타임스탬프 캐시 |

---

## 7. 디렉토리 구조 (목표)

```
2026_TV/
├── claude.md                   ← AI 컨텍스트 문서 (이 파일)
├── changelog.md                ← 작업 이력 (날짜별 기록)
├── docker-compose.yml          ← 전체 서비스 오케스트레이션
├── .env                        ← 실제 환경변수 (Git 제외)
├── .env.example                ← 환경변수 템플릿 (Git 포함)
├── .gitignore
│
├── docs/
│   ├── architecture.md         ← 상세 아키텍처 설계
│   └── schema_additions.sql    ← 신규 테이블 DDL
│
├── frontend/                   ← Next.js Web App (셋탑박스 에뮬레이터)
│   ├── Dockerfile
│   ├── package.json
│   ├── app/
│   │   ├── (channel)/          ← 실시간 채널 화면
│   │   ├── (vod)/              ← VOD 추천 화면
│   │   └── setup/              ← 초기 프로필 설정
│   └── components/
│       ├── ChannelPlayer/      ← 채널 플레이어 + Zapping
│       ├── ShoppingOverlay/    ← 쇼핑 매칭 UI
│       └── AdOverlay/          ← FAST 광고 오버레이
│
├── backend-api/                ← FastAPI 메인 API 서버
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py       ← pydantic-settings 환경변수
│       │   └── db.py           ← SQLAlchemy async engine
│       ├── api/v1/
│       │   ├── customers.py    ← 고객 API
│       │   ├── channels.py     ← 채널 API
│       │   ├── vod.py          ← VOD API
│       │   └── shopping.py     ← 쇼핑 매칭 API
│       └── models/             ← SQLAlchemy ORM 모델
│
├── nlp-api/                    ← NLP 추천 API 서버
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── recommender.py      ← 코사인 유사도 추천 엔진
│       ├── vectorizer.py       ← TF-IDF + KeyBERT 벡터화
│       └── api/
│           └── vod_proc.py     ← /admin/vod_proc 엔드포인트
│
└── ad-batch/                   ← FAST 광고 생성 배치 서버
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py             ← 스케줄러 진입점 (APScheduler)
        ├── scene_detector.py   ← PySceneDetect 씬 분할 (2026_ADWARE 재사용)
        ├── vision_analyzer.py  ← YOLO 객체 인식
        ├── ad_generator.py     ← 생성형 AI API 호출 (이미지/영상)
        └── timestamp_calculator.py ← 최적 삽입 타임스탬프 계산
```

---

## 8. 참조 프로젝트 재사용 현황

### 2026_TV_COMMERCE (`D:\20.WORKSPACE\2026_TV_COMMERCE`)
- **재사용**: DB 스키마 (`TB_CUST_INFO`, `TB_VOD_LOG`, `TB_VOD_META`, `TB_PROD_INFO`)
- **재사용**: FastAPI 앱 패턴 (`main.py`, `core/config.py`, `core/scheduler.py`)
- **재사용**: docker-compose 원격 배포 패턴 (외부 DB 연결, named volume)
- **재사용**: Next.js frontend 구조

### 2026_ADWARE (`D:\20.WORKSPACE\2026_ADWARE`)
- **재사용**: `scene_detector.py` — PySceneDetect ContentDetector 씬 분할
- **재사용**: DB ORM 패턴 (`shared/utils/db.py` — async SQLAlchemy)
- **재사용**: DB 스키마 (`jobs`, `scene_analyses`, `insertion_points`)
- **재사용**: Docker 멀티 서비스 구성 (redis + 다중 마이크로서비스)
- **재사용**: `vision.py` — YOLO 비전 분석 패턴
- **수정**: `insertion_points` → `TB_FAST_AD_INSERTION_POINT`로 확장 (에셋 FK 추가)

---

## 9. 핵심 설계 결정사항

1. **외부 DB 연결**: PostgreSQL은 서버에 이미 운영 중이므로 docker-compose에 DB 컨테이너 불포함. `DATABASE_URL` 환경변수로만 주입.
2. **광고 오버레이**: 원본 영상 파일 수정 없이 클라이언트 플레이어에서 타임스탬프 기반 UI 레이어로 노출 (비침습적 방식).
3. **오디오 배제**: FAST 광고 파이프라인의 씬 분할은 오디오 분석을 철저히 배제하고 비디오 프레임 기반으로만 처리.
4. **키즈 가중치**: `TB_USER_PROFILE_VECTOR`의 `kids_boost_score` 컬럼으로 키즈·애니메이션 추천 강제 포함.
5. **환경변수 격리**: 모든 접속 정보는 `.env`에서 주입, `.env.example`은 키 목록만 명세.

---

## 10. 개발 시작 체크리스트

- [ ] `.env` 파일 생성 (`.env.example` 기반)
- [ ] 외부 PostgreSQL 연결 테스트
- [ ] `docs/schema_additions.sql` 실행하여 신규 테이블 생성
- [ ] `docker-compose.yml` 작성 및 로컬 빌드 테스트
- [ ] frontend 셋톱박스 에뮬레이터 UI 설계
- [ ] backend-api 기본 라우터 구현
- [ ] nlp-api 벡터화 + 추천 엔진 구현
- [ ] ad-batch 파이프라인 구현 (씬 분할 → 비전 분석 → 광고 생성 → DB 적재)

