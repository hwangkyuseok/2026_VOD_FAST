# A-03. 용어 사전 (Glossary)

> **문서 정보**

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 2026_TV — 차세대 미디어 플랫폼 |
| 문서 번호 | A-03 |
| 문서 버전 | v1.0 |
| 작성일 | 2026-03-04 |
| 작성자 | 개발팀 |

---

## 1. 비즈니스 용어

| 용어 (한국어) | 영문/약어 | 정의 | 관련 테이블/컬럼 |
|-------------|----------|------|----------------|
| **금주의 무료 VOD** | Weekly Free VOD / 트랙1 | 매주 월요일 자동 선정되는 전 고객 공통 무료 VOD 10편. FAST 광고 삽입 대상. | `TB_WEEKLY_FREE_VOD` |
| **추천 VOD** | Recommended VOD / 트랙2 | 개인화 NLP 추천 엔진이 선정한 무료 VOD 10편. 광고 없음. | `TB_VOD_NLP_VECTOR`, `TB_USER_PROFILE_VECTOR` |
| **FAST 광고** | Free Ad-Supported Streaming TV | 무료 스트리밍 서비스의 재원으로 사용하는 광고. 영상 재생 중 오버레이 방식으로 삽입. | `TB_FAST_AD_ASSET`, `TB_FAST_AD_INSERTION_POINT` |
| **채널 전환 (채핑)** | Zapping | 채널을 빠르게 전환하는 행위. 목표 응답시간 500ms 이내. | `TB_CHANNEL_CONFIG`, `TB_WATCH_SESSION` |
| **커머스 채널** | Commerce Channel | 0번 채널. HV 쇼핑TV 에뮬레이션. 상품 목록 및 상담/구매 모달 제공. | `TB_PROD_INFO` |
| **편성표** | Channel Guide | 1~30번 채널 목록. `L` 키로 오버레이 표시. | `TB_CHANNEL_CONFIG` |
| **슬롯 기반 큐레이션** | Slot-based Curation | 트랙1 VOD 선정 시 장르별 슬롯(KIDS/DOCU_LIFE/ENT/ETC)으로 분류하여 콘텐츠 다양성 보장. | `TB_WEEKLY_FREE_VOD.SELECTION_REASON` |
| **렌탈 상품** | Rental Product | `is_rental='Y'`인 월 렌탈료 기반 상품. 가격을 "N원/월" 형식으로 표시. | `TB_PROD_INFO.IS_RENTAL` |
| **Cold Start** | Cold Start | 시청 이력이 전혀 없는 신규 유저에게 평점 기반 인기 콘텐츠를 추천하는 전략. | `TB_VOD_META.RATE` |
| **오버레이** | Overlay | 원본 영상 위에 UI 레이어를 겹쳐 표시하는 방식. 원본 영상 미수정 원칙. | `AdOverlay`, `ShoppingOverlay` |

---

## 2. 기술 용어

| 용어 | 약어/원어 | 정의 | 사용 컨텍스트 |
|------|---------|------|-------------|
| **슬라이딩 윈도우** | Sliding Window | 전체 VOD 목록 중 일부(6개)만 화면에 표시하고 포커스 이동에 따라 뷰 범위를 조정하는 방식 | VOD 페이지 트랙1/트랙2 |
| **키즈 부스트 점수** | kids_boost_score | 유저별 키즈·애니 장르 추천 가중치 (0.0~1.0). 연령 무관으로 키즈 콘텐츠 추천 보장. | `TB_USER_PROFILE_VECTOR.kids_boost_score` |
| **비전 태그** | vision_tags | YOLO 객체 감지 + CLIP 컨텍스트 태그를 통합한 광고 생성용 키워드 목록 (최대 10개) | `TB_FAST_AD_ASSET.SOURCE_KEYWORDS` |
| **모션 스코어** | motion_score | 씬 길이 기반 움직임 지표. 낮을수록 정적 구간 = 광고 삽입 적합. `1 - (씬길이/최대씬길이)` | `TB_FAST_AD_INSERTION_POINT.MOTION_SCORE` |
| **TF-IDF** | Term Frequency-Inverse Document Frequency | VOD 메타데이터 텍스트를 수치 벡터로 변환하는 NLP 기법. max_features=1000, ngram=(1,2) | `TB_VOD_NLP_VECTOR.tfidf_vector` |
| **KeyBERT** | Keyword BERT | KR-ELECTRA 기반 키워드 추출 모델. top_n=5, use_mmr=True | `TB_VOD_NLP_VECTOR.keybert_keywords` |
| **TF-IDF 피클** | tfidf.pkl | TF-IDF 벡터라이저 모델을 pickle 직렬화하여 Docker 볼륨에 영속화한 파일 | `/app/models/tfidf.pkl` |
| **씬 분할** | Scene Detection | PySceneDetect ContentDetector로 VOD를 씬 단위로 분할. threshold=30.0, 비디오 프레임만 분석 | `scene_detector.py` |
| **삽입 포인트** | Insertion Point | 광고를 삽입할 최적 타임스탬프 (씬 시작+1.0초). 최대 5개 선정. | `TB_FAST_AD_INSERTION_POINT` |
| **HLS** | HTTP Live Streaming | Apple이 개발한 적응형 스트리밍 프로토콜. 브라우저에서 `hls.js` 라이브러리로 지원 | `ChannelPlayer.tsx` |

---

## 3. 데이터 용어 (DB 컬럼명 ↔ 한국어명)

### 3.1 TB_VOD_META 주요 컬럼

| 컬럼명 | 한국어명 | 타입 | 설명 | v2 역할 |
|--------|---------|------|------|---------|
| `ASSET_ID` | 에셋 ID | VARCHAR(100) | VOD 고유 식별자, PK | - |
| `TTL` | 제목 | VARCHAR(255) | 원본 제목 | 시즌 테마 키워드 검색 대상 |
| `GENRE` | 장르 | VARCHAR(100) | 장르(대). 키즈/예능/다큐 등 | 슬롯 분류 기준 |
| `SMRY` | 줄거리 | TEXT | 요약 설명 | 4060 키워드 + 시즌 테마 검색 대상 |
| `USE_FL` | 사용여부 | INTEGER (0/1) | 1=사용 가능 | 하드 필터 |
| `SVC_APY_FL` | 서비스 적용 플래그 | INTEGER | 1=서비스 적용 | 하드 필터 |
| `THMBNL_FL` | 썸네일 여부 | INTEGER (0/1) | 1=썸네일 존재 | 하드 필터 |
| `DISP_RTM` | 상영시간 | VARCHAR(20) | `HH:MM:SS` 형식 문자열 | 하드 필터 (≥00:20:00) |
| `IS_HOT_FL` | 인기작 여부 | INTEGER (0/1) | 1=인기작 | 소프트 점수 +15 |
| `SCREEN_TP` | 화질 타입 | VARCHAR(50) | HD/FHD/UHD | 소프트 점수 +10 |
| `EPSD_NO` | 회차 번호 | INTEGER | 시리즈 회차 | 키즈 1화 유도 가점 |
| `SUPER_ASSET_NM` | 상위 에셋명 | VARCHAR(255) | 시리즈명 | 중복 제거 기준 |
| `RLSE_YEAR` | 출시 연도 | INTEGER | 제작 연도 | 중복 제거 시 우선순위 |
| `IS_FREE_YN` | 무료 여부 | CHAR(1) | Y=무료, N=유료 | 선정 후 Y로 변경 |
| `FAST_AD_ELIGIBLE_YN` | FAST광고 대상 여부 | CHAR(1) | Y=광고 삽입 가능 | 선정 후 Y로 변경 |
| `RATE` | 평점 | NUMERIC | 0.0~10.0 | Cold Start 정렬 기준 |

### 3.2 TB_WEEKLY_FREE_VOD

| 컬럼명 | 한국어명 | 타입 | 설명 |
|--------|---------|------|------|
| `ID` | 레코드 ID | UUID | PK (gen_random_uuid()) |
| `WEEK_START_YMD` | 주 시작일 | VARCHAR(8) | YYYYMMDD 형식 (월요일 기준) |
| `ASSET_ID` | 에셋 ID | VARCHAR(100) | FK → TB_VOD_META |
| `RANK_NO` | 선정 순위 | INTEGER | 1~10 |
| `SELECTION_SCORE` | 선정 점수 | NUMERIC | v2 소프트 점수 합계 |
| `SELECTION_REASON` | 선정 사유 | VARCHAR(100) | SLOT_KIDS / SLOT_DOCU / SLOT_ENT / SLOT_ETC |
| `AD_PIPELINE_STATUS` | 광고 파이프라인 상태 | VARCHAR(20) | PENDING → IN_PROGRESS → COMPLETED / FAILED |
| `IS_ACTIVE` | 활성 여부 | CHAR(1) | Y=현재 주, N=이전 주 |

### 3.3 선정 사유 코드표 (SELECTION_REASON)

| 코드 | 슬롯 | 장르 기준 | 최대 수량 |
|------|------|---------|---------|
| `SLOT_KIDS` | 키즈/애니 슬롯 | GENRE LIKE '%키즈%' OR '%애니%' | 3개 |
| `SLOT_DOCU` | 교양/다큐 슬롯 | GENRE LIKE '%다큐%' OR '%교양%' | 4개 |
| `SLOT_ENT` | 예능/음악 슬롯 | GENRE LIKE '%예능%' OR '%연예/오락%' | 2개 |
| `SLOT_ETC` | 기타/명품 슬롯 | 위에 해당하지 않는 모든 장르 | 1개 |

---

## 4. 환경변수 용어표

| 변수명 | 사용 서비스 | 기본값 | 설명 |
|--------|-----------|--------|------|
| `DATABASE_URL` | 전체 | - | PostgreSQL 연결 URL |
| `REDIS_URL` | be, nlp, batch | - | Redis 연결 URL |
| `WEEKLY_FREE_VOD_COUNT` | ad-batch | `10` | 주간 무료 VOD 선정 수 |
| `AD_BATCH_CRON` | ad-batch | `0 2 * * 1` | 배치 스케줄 (cron 표현식) |
| `CLIP_ENABLED` | ad-batch | `true` | CLIP 모델 활성화. CPU 환경에선 `false` 권장 |
| `KIDS_BOOST_SCORE` | nlp-api | `0.3` | 키즈·애니 추천 가중치 (0.0~1.0) |
| `KIDS_GENRE_CODES` | nlp-api | `KIDS,ANIME,ANIMATION` | 키즈 장르 코드 목록 |
| `CORS_ORIGINS` | backend-api | - | 허용 CORS 오리진 목록 |
| `IMAGE_GEN_API_KEY` | ad-batch | - | 이미지 생성 AI API 키 |
| `VIDEO_GEN_API_KEY` | ad-batch | - | 영상 생성 AI API 키 |

---

## 5. 시스템 약어 목록

| 약어 | 풀네임 | 설명 |
|------|--------|------|
| FAST | Free Ad-Supported Streaming TV | 광고 기반 무료 스트리밍 모델 |
| SRS | Software Requirements Specification | 소프트웨어 요구사항 정의서 |
| SAD | System Architecture Document | 시스템 아키텍처 설계서 |
| ERD | Entity-Relationship Diagram | 개체-관계 다이어그램 |
| NLP | Natural Language Processing | 자연어 처리 |
| TF-IDF | Term Frequency-Inverse Document Frequency | 단어 빈도-역문서 빈도 |
| YOLO | You Only Look Once | 실시간 객체 감지 딥러닝 모델 |
| CLIP | Contrastive Language-Image Pre-training | OpenAI의 멀티모달 모델 |
| COCO | Common Objects in Context | 객체 감지 벤치마크 데이터셋 (80 클래스) |
| HLS | HTTP Live Streaming | Apple 개발 적응형 스트리밍 프로토콜 |
| API | Application Programming Interface | 애플리케이션 프로그래밍 인터페이스 |
| UUID | Universally Unique Identifier | 전역 고유 식별자 |
| ORM | Object-Relational Mapping | 객체-관계 매핑 (SQLAlchemy) |
