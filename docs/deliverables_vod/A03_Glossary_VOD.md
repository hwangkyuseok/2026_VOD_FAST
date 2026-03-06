# A-03. 용어 사전 — VOD 서비스 (Glossary)

> **문서 정보**

| 항목 | 내용 |
|------|------|
| 프로젝트명 | 2026_TV — VOD 서비스 |
| 문서 번호 | A-03 (VOD) |
| 문서 버전 | v1.0 |
| 작성일 | 2026-03-04 |

---

## 1. 비즈니스 용어

| 용어 | 영문/약어 | 정의 | 관련 테이블/컬럼 |
|------|---------|------|----------------|
| **금주의 무료 VOD** | Weekly Free VOD / 트랙1 | 매주 월요일 배치로 자동 선정되는 전 고객 공통 무료 VOD 10편. FAST 광고 삽입 대상. | `TB_WEEKLY_FREE_VOD` |
| **추천 VOD** | Recommended VOD / 트랙2 | 개인화 NLP 추천 엔진이 선정한 무료 VOD 10편. 광고 없음. | `TB_USER_PROFILE_VECTOR`, `TB_VOD_NLP_VECTOR` |
| **FAST 광고** | Free Ad-Supported Streaming TV | 무료 스트리밍 서비스의 광고 수익 모델. VOD 재생 중 오버레이 방식으로 삽입. | `TB_FAST_AD_ASSET`, `TB_FAST_AD_INSERTION_POINT` |
| **슬롯 기반 큐레이션** | Slot-based Curation | 트랙1 VOD 선정 시 장르별 할당 슬롯(KIDS/DOCU_LIFE/ENT/ETC)으로 분류하여 콘텐츠 다양성 보장 | `SELECTION_REASON` |
| **Cold Start** | Cold Start | 시청 이력이 전혀 없는 신규 유저에게 평점 기반 인기 콘텐츠를 추천하는 전략 | `TB_VOD_META.RATE` |
| **오버레이** | Overlay | 원본 영상 위에 UI 레이어를 겹쳐 표시하는 방식. 원본 영상 파일 무수정 원칙. | `AdOverlay` 컴포넌트 |
| **슬라이딩 윈도우** | Sliding Window | 전체 VOD 10개 목록 중 6개만 화면에 표시하고 포커스 이동에 따라 뷰 범위를 조정하는 방식 | VOD 페이지 트랙1/트랙2 |
| **키즈 부스트** | kids_boost_score | 유저별 키즈·애니 장르 추천 가중치 (0.1~1.0). 연령 무관으로 키즈 콘텐츠 추천 보장. | `TB_USER_PROFILE_VECTOR.KIDS_BOOST_SCORE` |

---

## 2. 기술 용어

| 용어 | 약어/원어 | 정의 |
|------|---------|------|
| **TF-IDF** | Term Frequency-Inverse Document Frequency | VOD 메타데이터 텍스트를 수치 벡터로 변환하는 NLP 기법. `max_features=1000`, `ngram=(1,2)` |
| **KeyBERT** | Keyword BERT | KR-ELECTRA 기반 키워드 추출 모델. `top_n=5`, `use_mmr=True` |
| **KR-ELECTRA** | Korean ELECTRA | 한국어 NLP 사전학습 모델 (`snunlp/KR-ELECTRA-discriminator`) |
| **코사인 유사도** | Cosine Similarity | 두 벡터 간의 각도로 유사도를 측정. 1에 가까울수록 유사. `유저벡터 ↔ VOD벡터` 비교에 사용 |
| **tfidf.pkl** | TF-IDF Pickle | TF-IDF 벡터라이저 모델을 pickle 직렬화하여 Docker 볼륨에 영속화한 파일 |
| **비전 태그** | vision_tags | YOLO 객체 감지 + CLIP 컨텍스트 태그를 통합한 광고 생성용 키워드 목록 (최대 10개) |
| **모션 스코어** | motion_score | 씬 길이 기반 움직임 지표. `1 - (씬길이/최대씬길이)`. 낮을수록 광고 삽입 적합 |
| **씬 분할** | Scene Detection | PySceneDetect ContentDetector로 VOD를 씬 단위로 분할. `threshold=30.0` |
| **삽입 포인트** | Insertion Point | 광고를 삽입할 최적 타임스탬프 (씬 시작+1.0초). 최대 5개 선정. |
| **프로필 벡터** | Profile Vector | 유저의 시청 이력(가중 평균)에서 계산된 선호도 벡터. TF-IDF 공간에서 표현. |

---

## 3. 데이터 용어 (DB 컬럼명 ↔ 한국어명)

### TB_VOD_META — 큐레이션 핵심 컬럼

| 컬럼명 | 한국어명 | 설명 | v2 역할 |
|--------|---------|------|---------|
| `TTL` | 제목 | 원본 제목 | 시즌 테마 키워드 검색 대상 |
| `GENRE` | 장르 | 장르(대). 키즈/예능/다큐 등 | **슬롯 분류 기준** |
| `SMRY` | 줄거리 | 요약 설명 | 4060 키워드 + 시즌 테마 검색 |
| `USE_FL` | 사용여부 | 1=사용 가능 | **하드 필터** |
| `SVC_APY_FL` | 서비스 적용 플래그 | 1=서비스 적용 | **하드 필터** |
| `THMBNL_FL` | 썸네일 여부 | 1=썸네일 존재 | **하드 필터** |
| `DISP_RTM` | 상영시간 | `HH:MM:SS` 문자열 | **하드 필터** (≥00:20:00) |
| `IS_HOT_FL` | 인기작 여부 | 0/1 | **소프트 점수 +15** |
| `SCREEN_TP` | 화질 타입 | HD/FHD/UHD | **소프트 점수 +10** |
| `EPSD_NO` | 회차 번호 | 시리즈 회차 | 키즈 1화 유도 가점 |
| `SUPER_ASSET_NM` | 시리즈명 | 상위 에셋명 | **중복 제거 기준** |
| `RLSE_YEAR` | 출시 연도 | 제작 연도 | 중복 제거 우선순위 |
| `IS_FREE_YN` | 무료 여부 | Y=무료, N=유료 | 선정 후 Y 변경, 다음 주 배치 전 N 복원 |
| `FAST_AD_ELIGIBLE_YN` | FAST광고 대상 | Y=광고 삽입 가능 | 트랙1 선정 후 Y 변경 |

### 선정 사유 코드표 (SELECTION_REASON)

| 코드 | 슬롯명 | 장르 분류 기준 | 최대 수량 |
|------|--------|-------------|---------|
| `SLOT_KIDS` | 키즈/애니 슬롯 | GENRE LIKE '%키즈%' OR '%애니%' | **3개** |
| `SLOT_DOCU` | 교양/다큐 슬롯 | GENRE LIKE '%다큐%' OR '%교양%' | **4개** |
| `SLOT_ENT` | 예능/음악 슬롯 | GENRE LIKE '%예능%' OR '%연예/오락%' | **2개** |
| `SLOT_ETC` | 기타/명품 슬롯 | 위에 해당하지 않는 모든 장르 | **1개** |

### AD_PIPELINE_STATUS 코드표

| 코드 | 의미 |
|------|------|
| `PENDING` | 배치 선정 완료, 파이프라인 대기 중 |
| `IN_PROGRESS` | 씬 분할 / 비전 분석 / 광고 생성 진행 중 |
| `COMPLETED` | 전체 파이프라인 완료 |
| `FAILED` | 오류 발생으로 중단 |

---

## 4. 환경변수 용어표 (VOD 범위)

| 변수명 | 사용 서비스 | 기본값 | 설명 |
|--------|-----------|--------|------|
| `DATABASE_URL` | 전체 | - | PostgreSQL 연결 URL |
| `REDIS_URL` | be, nlp, batch | - | Redis 연결 URL |
| `WEEKLY_FREE_VOD_COUNT` | ad-batch | `10` | 주간 무료 VOD 선정 목표 수 |
| `AD_BATCH_CRON` | ad-batch | `0 2 * * 1` | 배치 스케줄 (cron, 매주 월 02:00) |
| `CLIP_ENABLED` | ad-batch | `true` | CLIP 모델 활성화. CPU 환경엔 `false` 권장 |
| `IMAGE_GEN_API_KEY` | ad-batch | - | 이미지 생성 AI API 키 (DALL-E 3 등) |
| `VIDEO_GEN_API_KEY` | ad-batch | - | 영상 생성 AI API 키 (RunwayML 등) |
| `KIDS_BOOST_SCORE` | nlp-api | `0.3` | 키즈·애니 추천 가중치 (0.0~1.0) |
| `KIDS_GENRE_CODES` | nlp-api | `KIDS,ANIME,ANIMATION` | 키즈 장르 코드 목록 |

---

## 5. 약어 목록 (VOD 범위)

| 약어 | 풀네임 | 설명 |
|------|--------|------|
| FAST | Free Ad-Supported Streaming TV | 광고 기반 무료 스트리밍 수익 모델 |
| NLP | Natural Language Processing | 자연어 처리 |
| TF-IDF | Term Frequency-Inverse Document Frequency | 단어 빈도-역문서 빈도 |
| YOLO | You Only Look Once | 실시간 객체 감지 딥러닝 모델 (v8n 사용) |
| CLIP | Contrastive Language-Image Pre-training | OpenAI 멀티모달 모델 |
| COCO | Common Objects in Context | 객체 감지 데이터셋 (80 클래스) |
| ORM | Object-Relational Mapping | 객체-관계 매핑 (SQLAlchemy) |
| CTE | Common Table Expression | SQL 공통 테이블 표현식 (v2 쿼리에 3단계 CTE 사용) |
