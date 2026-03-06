# 2026_TV — 상세 아키텍처 설계

---

## 1. 전체 시스템 구성도

```
                        [사용자 브라우저]
                               │
                               ▼
                    ┌──────────────────┐
                    │   frontend:3000   │  Next.js 14+ App Router
                    │  (셋탑박스 에뮬)  │  TypeScript + Tailwind
                    └────────┬─────────┘
                             │ REST API
                    ┌────────▼─────────┐
                    │  backend-api:8000 │  FastAPI (Python)
                    │   메인 API 서버   │  SQLAlchemy async
                    └──┬──────────┬────┘
                       │          │
             ┌─────────▼──┐   ┌──▼──────────────┐
             │  nlp-api   │   │    ad-batch      │
             │   :8001    │   │  (Batch Worker)  │
             │ NLP 추천   │   │  FAST 광고 파이프│
             └─────────┬──┘   └──────────┬───────┘
                       │                 │
              ┌────────▼─────────────────▼────────┐
              │              Redis :6379            │
              │         (큐 + 세션 캐시)            │
              └───────────────────────────────────┘
                       │
              ┌────────▼─────────────────────────┐
              │   PostgreSQL :5432  (외부 운영)    │
              │   Host: YOUR_SERVER_IP / hv02     │
              └──────────────────────────────────┘
```

---

## 2. 컨테이너별 상세 설계

### 2.1 frontend (Next.js)

**역할**: 셋탑박스 UI 에뮬레이터 + 사용자 인터페이스

**핵심 화면 구성**:
```
/setup                   ← 초기 전원 ON, 프로필 설정
/channel/[id]            ← 실시간 채널 시청 (Zapping 지원)
/vod                     ← VOD 메인 (트랙1 + 트랙2)
/vod/[assetId]           ← VOD 플레이어 (FAST 광고 오버레이 포함)
/admin/vod_proc          ← NLP 추천 관리 (백오피스)
```

**핵심 컴포넌트**:
- `ChannelPlayer`: HLS.js 기반 스트리밍 + 리모컨 키 이벤트 (Up/Down Zapping)
- `ShoppingOverlay`: 하단/측면 쇼핑 정보 UI (비전 AI 매칭 결과 표시)
- `AdOverlay`: FAST 광고 오버레이 (타임스탬프 도달 시 렌더링, 원본 플레이어 위에 겹쳐 표시)
- `VodRecommendCards`: 추천 사유 텍스트 포함 VOD 카드 (트랙2)
- `RemoteControl`: 가상 리모컨 UI (채널 증감, 음량, 메뉴)

**환경변수**:
- `NEXT_PUBLIC_API_URL`: backend-api 주소 (빌드 시 주입)
- `NEXT_PUBLIC_NLP_API_URL`: nlp-api 주소

---

### 2.2 backend-api (FastAPI)

**역할**: 메인 비즈니스 로직 API 서버

**API 라우터 구성**:
```
GET  /health                         ← 헬스체크
GET  /api/v1/channels                ← 채널 목록 30개
GET  /api/v1/channels/{id}/stream    ← 채널 스트림 URL
POST /api/v1/watch/start             ← 시청 세션 시작 (TB_WATCH_SESSION)
POST /api/v1/watch/end               ← 시청 세션 종료 + 이력 저장

GET  /api/v1/vod/weekly-free         ← 금주 무료 VOD 10개 (트랙1)
GET  /api/v1/vod/personalized        ← 개인화 무료 VOD 10개 (트랙2, nlp-api 호출)
GET  /api/v1/vod/{assetId}           ← VOD 상세 + 광고 삽입 타임스탬프
GET  /api/v1/vod/{assetId}/ad-points ← FAST 광고 삽입 포인트 조회

GET  /api/v1/shopping/match          ← 비전 AI 쇼핑 상품 매칭
GET  /api/v1/shopping/products       ← 쇼핑 상품 목록 (TB_PROD_INFO)

GET  /api/v1/customers/{userId}      ← 고객 프로필 조회
PUT  /api/v1/customers/{userId}/profile ← 프로필 업데이트
```

**의존성**:
- PostgreSQL (SQLAlchemy async)
- Redis (캐시: 채널 목록, 금주 VOD)
- nlp-api (personalized VOD 추천 요청 위임)

---

### 2.3 nlp-api (FastAPI)

**역할**: NLP 기반 VOD 추천 엔진

**API 엔드포인트**:
```
POST /admin/vod_proc/vectorize      ← VOD 메타데이터 전체 벡터화 (배치)
POST /admin/vod_proc/recommend      ← 특정 유저 개인화 추천 10개 반환
GET  /admin/vod_proc/vectors/{id}   ← VOD 벡터 조회
POST /admin/vod_proc/rebuild-user   ← 유저 프로필 벡터 재계산
```

**NLP 추천 파이프라인 (`/admin/vod_proc/recommend`)**:
```python
# 1. 유저 프로필 벡터 조회 (TB_USER_PROFILE_VECTOR)
#    - 없으면 TB_VOD_LOG 기반으로 실시간 생성

# 2. 무료 VOD 풀 벡터 조회 (TB_VOD_NLP_VECTOR WHERE IS_FREE_YN='Y')

# 3. 코사인 유사도 계산
similarities = cosine_similarity(user_vector, vod_vectors)

# 4. 키즈·애니메이션 가중치 적용 (절대 배제 금지)
for vod in vod_pool:
    if vod.genre in KIDS_GENRE_CODES:
        similarities[vod.id] += user_profile.kids_boost_score

# 5. 상위 10개 선정 + 추천 사유 생성
#    "최근 시청한 액션 장르와 유사합니다", "키즈 콘텐츠 이용 패턴 기반 추천" 등
```

**벡터화 방법**:
- 텍스트 소스: `TB_VOD_META.DESCRIPTION + HASH_TAG + GENRE + GENRE_OF_CT_CL + SMRY`
- 모델: `TF-IDF Vectorizer` (빠른 초기 벡터화) + `KeyBERT` (키워드 추출 강화)
- 한국어 지원: `snunlp/KR-ELECTRA-discriminator` 또는 `jhgan/ko-sroberta-multitask`

---

### 2.4 ad-batch (Python Batch Worker)

**역할**: FAST 광고 생성 파이프라인 (주 1회 APScheduler 배치)

**파이프라인 흐름**:
```
[트리거: 매주 월요일 02:00 KST]
        │
        ▼
1. TB_WEEKLY_FREE_VOD에서 이번 주 10개 VOD 조회
        │
        ▼
2. 각 VOD 영상 파일 로드 + jobs 테이블에 작업 등록
        │
        ▼
3. scene_detector.py — PySceneDetect ContentDetector
   - 비디오 프레임만 분석 (오디오 완전 배제)
   - 씬 전환점 탐지 → SceneSegment 목록 생성
   - scene_analyses 테이블에 저장
        │
        ▼
4. vision_analyzer.py — YOLOv8 객체 인식
   - 각 씬 키프레임에서 객체/행동 키워드 추출
   - vision_tags JSONB로 scene_analyses 업데이트
        │
        ▼
5. timestamp_calculator.py — 최적 삽입 타임스탬프 계산
   - 저움직임 구간 (광학 흐름 분석)
   - 씬 전환 직후 구간
   - confidence 점수 계산
        │
        ▼
6. ad_generator.py — 생성형 AI API 호출
   - vision_tags → 프롬프트 텍스트 변환
   - 이미지 생성 API: 상품 썸네일/팝업 이미지
   - 비디오 생성 API: 무음 3~5초 숏폼
   - 결과물 → AD_ASSET_DIR 저장
        │
        ▼
7. TB_FAST_AD_ASSET + TB_FAST_AD_INSERTION_POINT에 적재
   - jobs 상태 'completed'로 갱신
```

**재사용 코드 (2026_ADWARE)**:
- `scene_detector.py` → `PySceneDetect ContentDetector` 로직 그대로 이식
- `shared/utils/db.py` → SQLAlchemy async 연결 패턴 이식
- `services/analyzer/vision.py` → YOLO 비전 분석 패턴 참조

---

## 3. 데이터 흐름도

### 3.1 채널 Zapping 흐름
```
사용자 Up/Down 키 입력
  → frontend: 채널 번호 변경 + TB_WATCH_SESSION 종료
  → GET /api/v1/channels/{newId}/stream
  → HLS.js 새 스트림 URL 로드
  → 채널 변경 완료 (목표: 500ms 이내)
```

### 3.2 실시간 쇼핑 매칭 흐름
```
채널 시청 중 (주기적 스크린샷 또는 프레임)
  → POST /api/v1/shopping/match { frame_base64 }
  → YOLO 객체 인식 → 키워드 추출
  → TB_PROD_INFO에서 유사 상품 검색
  → ShoppingOverlay 컴포넌트에 결과 표시
```

### 3.3 VOD 재생 + FAST 광고 오버레이 흐름
```
사용자 VOD 선택 (트랙1 한정 광고 적용)
  → GET /api/v1/vod/{assetId}/ad-points
  → TB_FAST_AD_INSERTION_POINT에서 타임스탬프 목록 조회
  → 플레이어에 타임스탬프 등록

VOD 재생 중...
  → 플레이어 currentTime이 등록 타임스탬프 도달
  → AdOverlay 컴포넌트 활성화
  → TB_FAST_AD_ASSET의 에셋(이미지/비디오) 로드 + 표시
  → 원본 영상은 계속 재생 (오버레이 방식, 원본 파일 수정 없음)
```

---

## 4. Docker Compose 구성 (설계안)

```yaml
version: "3.9"

services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env
    depends_on: [backend-api]

  backend-api:
    build: ./backend-api
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  nlp-api:
    build: ./nlp-api
    ports: ["8001:8001"]
    env_file: .env
    depends_on: [redis]
    # GPU 지원 시 아래 주석 해제
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]

  ad-batch:
    build: ./ad-batch
    env_file: .env
    volumes:
      - ad_assets:/app/data/ad_assets
      - vod_source:/app/data/vod:ro
    depends_on: [redis]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  # ※ PostgreSQL은 외부 운영 중 → 컨테이너 미포함
  # 연결: postgresql+asyncpg://postgres01:***@YOUR_SERVER_IP:5432/hv02

volumes:
  ad_assets:
  vod_source:

networks:
  default:
    name: tv_network
```

---

## 5. 보안 고려사항

1. **환경변수 격리**: 모든 접속 정보는 `.env`에서만 관리, `.gitignore`에 `.env` 추가
2. **CORS**: `CORS_ORIGINS` 환경변수로 허용 오리진 제한 (프로덕션에서 `*` 사용 금지)
3. **DB 연결**: `DATABASE_URL`에 비밀번호 포함 → 환경변수로만 주입
4. **API 키**: 생성형 AI API 키는 ad-batch 서비스에서만 사용, 외부 노출 차단
5. **내부 서비스 통신**: backend-api → nlp-api 호출 시 Docker 내부 네트워크 사용 (포트 외부 노출 최소화)

---

## 6. 성능 설계

| 항목 | 목표 | 방법 |
|------|------|------|
| 채널 전환 | < 500ms | HLS 프리로드, Redis 채널 URL 캐시 |
| VOD 추천 | < 200ms | 유저 벡터 사전 계산 후 Redis 캐시 |
| 광고 오버레이 | < 100ms | 에셋 사전 생성 + CDN/로컬 캐시 |
| 쇼핑 매칭 | < 1s | YOLO nano 모델, 비동기 처리 |
| NLP 벡터화 | 배치 처리 | 주 1회 오프피크 시간대 실행 |
