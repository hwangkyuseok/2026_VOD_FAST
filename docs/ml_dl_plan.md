# 2026_TV — ML/DL 모델 활용 계획

> 기능 영역별 모델 선택 근거, 입출력 스펙, 배포 전략을 정의합니다.

---

## 모델 전체 지도

```
┌─────────────────────────────────────────────────────────────────────┐
│                        기능 영역별 모델 배치                          │
│                                                                      │
│  [nlp-api 컨테이너]              [ad-batch 컨테이너]                  │
│  ┌──────────────────────┐        ┌──────────────────────────────┐    │
│  │ ① TF-IDF Vectorizer  │        │ ③ PySceneDetect              │    │
│  │   (scikit-learn)     │        │   ContentDetector (씬 분할)   │    │
│  │ ② KeyBERT            │        │ ④ YOLOv8n (객체 인식)         │    │
│  │   (KR-ELECTRA)       │        │ ⑤ RAFT/Farneback (광학흐름)  │    │
│  └──────────────────────┘        │ ⑥ Gen AI API (이미지 생성)   │    │
│                                  │ ⑦ Gen AI API (영상 생성)     │    │
│  [backend-api 컨테이너]          └──────────────────────────────┘    │
│  ┌──────────────────────┐                                            │
│  │ ⑧ YOLOv8n (실시간   │                                            │
│  │   쇼핑 매칭, 경량)   │                                            │
│  └──────────────────────┘                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 영역 1: NLP 추천 엔진 (nlp-api)

### 모델 ① TF-IDF Vectorizer

| 항목 | 내용 |
|------|------|
| **라이브러리** | `scikit-learn.TfidfVectorizer` |
| **역할** | VOD 메타데이터 텍스트를 고차원 희소 벡터로 변환 |
| **입력** | `TB_VOD_META.DESCRIPTION + HASH_TAG + GENRE + SMRY` 연결 텍스트 |
| **출력** | 희소 벡터 (차원: 어휘 크기, 약 5,000~20,000) → JSONB로 DB 저장 |
| **전처리** | 한국어 형태소 분석기(`konlpy.Okt` 또는 `kiwi`) → 명사/동사 추출 후 TF-IDF 적용 |
| **갱신 주기** | 전체 VOD 풀 변경 시 (주 1회 배치 병행) |
| **선택 이유** | 빠른 학습·추론, 설명 가능, 추천 사유 텍스트 생성에 직접 활용 가능 |

### 모델 ② KeyBERT (KR-ELECTRA 기반)

| 항목 | 내용 |
|------|------|
| **라이브러리** | `keybert.KeyBERT` |
| **Backbone** | `snunlp/KR-ELECTRA-discriminator` (한국어 특화) |
| **대안** | `jhgan/ko-sroberta-multitask` (문장 유사도 특화, 추천 품질 우선 시 선택) |
| **역할** | 각 VOD에서 대표 키워드 5~10개 추출, 추천 사유 생성에 활용 |
| **입력** | VOD 설명 텍스트 (최대 512 토큰) |
| **출력** | `[{keyword: "액션", score: 0.82}, ...]` → `TB_VOD_NLP_VECTOR.KEYBERT_KEYWORDS` |
| **추천 사유 예시** | "최근 시청한 **액션, 추격**과 유사한 콘텐츠입니다" |
| **GPU 필요** | 배치 처리 시 권장, 없으면 CPU로 동작 가능 (속도 저하) |

### 추천 파이프라인 상세

```python
# 1. 유저 프로필 벡터 생성
#    TB_VOD_LOG에서 최근 90일 시청 이력 조회
#    → 시청한 VOD들의 TF-IDF 벡터 가중 평균 (USE_TMS 가중치 적용)
user_vector = weighted_avg(
    [vod_vectors[asset_id] for asset_id in watched_assets],
    weights=[watch_time for watch_time in watch_times]
)

# 2. 코사인 유사도 계산
similarities = cosine_similarity(user_vector, free_vod_vectors)  # shape: (1, N)

# 3. 키즈·애니 가중치 (비즈니스 룰 강제 적용)
for i, vod in enumerate(free_vod_pool):
    if vod.is_kids_genre:
        similarities[0][i] += user_profile.kids_boost_score  # 최소 +0.1 보장

# 4. 상위 10개 선정
top_10_indices = similarities[0].argsort()[-10:][::-1]

# 5. 추천 사유 생성 (설명 가능 AI)
#    겹치는 KeyBERT 키워드 교집합으로 사유 텍스트 자동 생성
reason = generate_reason(user_keywords, vod_keywords)
# 예: "최근 시청한 '액션, 형사' 키워드와 유사합니다"
# 예: "키즈 콘텐츠 이용 패턴을 반영하여 추천합니다" (is_kids_genre=True)
```

---

## 영역 2: FAST 광고 파이프라인 (ad-batch)

### 모델 ③ PySceneDetect ContentDetector (씬 분할)

| 항목 | 내용 |
|------|------|
| **라이브러리** | `scenedetect.ContentDetector` |
| **역할** | 비디오 프레임 픽셀 변화량 기반 씬 전환점 탐지 |
| **입력** | VOD 원본 영상 파일 (mp4, mkv 등) |
| **출력** | `SceneSegment` 목록 (start_time, end_time, keyframe_path) |
| **핵심 파라미터** | `threshold=30.0` (낮을수록 민감, 30이 일반 드라마/영화 기준) |
| **오디오 처리** | **완전 배제** — `open_video()` 후 비디오 스트림만 분석 |
| **코드 출처** | `2026_ADWARE/services/preprocessor/scene_detector.py` 그대로 이식 |
| **DB 저장** | `scene_analyses` 테이블 (job_id, scene_index, start_time, end_time) |

### 모델 ④ YOLOv8 (객체 인식 — 광고 파이프라인용)

| 항목 | 내용 |
|------|------|
| **라이브러리** | `ultralytics.YOLO` |
| **모델 크기** | `yolov8s.pt` (small) — 배치 처리이므로 속도보다 정확도 우선 |
| **역할** | 각 씬 키프레임에서 객체 탐지 → 광고 프롬프트 생성용 키워드 추출 |
| **입력** | 씬 키프레임 PNG (씬 분할 단계에서 추출) |
| **출력** | `[{label: "person", conf: 0.92}, {label: "car", conf: 0.87}, ...]` |
| **DB 저장** | `scene_analyses.vision_tags` JSONB |
| **코드 출처** | `2026_ADWARE/services/analyzer/vision.py` 참조 |

**SlowFast(행동 인식) 도입 검토**:
- 기획서에 언급된 "인물의 행동/상황 키워드 추출"은 YOLOv8만으로 객체 탐지 수준 가능
- 행동 분류(달리기, 요리하는 등)까지 필요하면 `SlowFast-R50` 추가 도입
- **현재 계획: YOLOv8으로 1차 구현, 광고 품질 평가 후 SlowFast 도입 여부 결정**
- SlowFast는 GPU 필수이며 추론 시간이 길어 배치 처리 시간 대폭 증가 주의

### 모델 ⑤ 광학 흐름 (Optical Flow) — 광고 삽입 타임스탬프 계산

| 항목 | 내용 |
|------|------|
| **라이브러리** | `cv2.calcOpticalFlowFarneback` (OpenCV, CPU 기반) |
| **대안** | RAFT (딥러닝 기반, GPU 필요, 더 정확) |
| **역할** | 연속 프레임 간 픽셀 이동량 계산 → 저움직임 구간 탐지 |
| **입력** | 연속 비디오 프레임 (1초당 2~5프레임 샘플링) |
| **출력** | 구간별 `motion_score` → `TB_FAST_AD_INSERTION_POINT.MOTION_SCORE` |
| **삽입 기준** | motion_score 하위 20% 구간 + 씬 전환 직후 2초 이내 |
| **선택 이유** | CPU만으로 동작 가능, 2026_ADWARE `insertion-detector/scorer.py` 패턴 참조 |

```python
# 저움직임 구간 탐지 알고리즘
def calc_motion_score(frame1, frame2) -> float:
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(gray1, gray2, None,
                                        pyr_scale=0.5, levels=3, winsize=15,
                                        iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
    magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
    return float(magnitude.mean())  # 낮을수록 저움직임 → 광고 삽입 적합
```

### 모델 ⑥⑦ 생성형 AI API (이미지/비디오 생성)

**이미지 생성 (모델 ⑥)**:

| 항목 | 옵션 A (권장) | 옵션 B | 옵션 C |
|------|--------------|--------|--------|
| **서비스** | OpenAI DALL-E 3 | Stability AI SDXL | Google Imagen |
| **프롬프트 예시** | `"고급 노트북 상품 광고 이미지, 화이트 배경, 한국 쇼핑몰 스타일"` | 동일 | 동일 |
| **출력** | 1024×1024 PNG | 1024×1024 PNG | 1024×1024 PNG |
| **비용** | $0.040/장 | $0.002/장 | 별도 |
| **선택 기준** | 품질 우선 | 비용 우선 | — |

**비디오 생성 (모델 ⑦)**:

| 항목 | 옵션 A | 옵션 B |
|------|--------|--------|
| **서비스** | RunwayML Gen-3 Alpha | Kling AI |
| **목표** | **무음(Silent) 3~5초** 숏폼 영상 | 동일 |
| **출력** | MP4, 720p 이상 | MP4, 1080p |
| **주의** | API 응답 지연 가능 → 비동기 폴링 방식으로 처리 | 동일 |
| **대체 전략** | 이미지 슬라이드쇼 → ffmpeg로 무음 비디오 합성 (API 장애 시 폴백) | — |

**프롬프트 생성 로직**:
```python
def build_ad_prompt(vision_tags: list, context: str) -> str:
    # YOLO 감지 객체 → 쇼핑 카테고리 매핑
    # 예: person → lifestyle, car → automotive, food → restaurant
    keywords = [tag["label"] for tag in vision_tags if tag["conf"] > 0.6]
    category = map_to_shopping_category(keywords)
    return f"한국 온라인 쇼핑 광고 이미지, {category} 상품, 깔끔한 배경, 고해상도 상업 사진 스타일"
```

---

## 영역 3: 실시간 쇼핑 매칭 (backend-api)

### 모델 ⑧ YOLOv8n (실시간 경량 객체 인식)

| 항목 | 내용 |
|------|------|
| **모델 크기** | `yolov8n.pt` (nano) — 실시간 응답 필수이므로 최경량 선택 |
| **역할** | 채널 시청 중 화면 프레임에서 객체 인식 → TB_PROD_INFO 상품 매칭 |
| **입력** | 클라이언트가 주기적으로 전송하는 프레임 (Base64 인코딩 또는 멀티파트) |
| **출력** | 탐지된 객체 레이블 목록 → DB 상품 텍스트 검색 |
| **호출 주기** | 5초에 1회 (클라이언트 주도, 서버 부하 제어) |
| **매칭 로직** | YOLO 레이블 → 카테고리 매핑 → `TB_PROD_INFO.CATEGORY ILIKE %keyword%` |
| **목표 응답 시간** | < 1초 |

---

## 모델별 리소스 요구사항

| 모델 | CPU | RAM | GPU | 실행 시점 |
|------|-----|-----|-----|-----------|
| TF-IDF Vectorizer | 낮음 | 1~2GB | 불필요 | 배치 (주 1회) |
| KeyBERT (KR-ELECTRA) | 높음 | 2~4GB | 권장 | 배치 (주 1회) |
| PySceneDetect | 보통 | 1GB | 불필요 | 배치 (주 1회) |
| YOLOv8s (광고용) | 높음 | 2GB | 권장 | 배치 (주 1회) |
| Optical Flow (Farneback) | 보통 | 1GB | 불필요 | 배치 (주 1회) |
| Gen AI API (이미지) | 없음 | 없음 | 없음 (외부) | 배치 (주 1회) |
| Gen AI API (비디오) | 없음 | 없음 | 없음 (외부) | 배치 (주 1회) |
| YOLOv8n (쇼핑 실시간) | 낮음 | 0.5GB | 불필요 | 실시간 |

> **현재 서버(YOUR_SERVER_IP) GPU 유무 미확인** → docker-compose GPU 설정은 주석 처리 후, 확인 후 활성화

---

## 모델 파일 관리 전략

```
ad-batch/
└── models/
    ├── yolov8s.pt          ← Ultralytics 자동 다운로드 (최초 실행 시)
    └── kr_electra/         ← HuggingFace 캐시 (컨테이너 볼륨 마운트)

nlp-api/
└── models/
    └── kr_electra/         ← HuggingFace 캐시 공유 볼륨
```

- HuggingFace 모델은 `TRANSFORMERS_CACHE` 환경변수로 볼륨 경로 지정
- YOLOv8 모델은 `YOLO_MODEL_PATH` 환경변수로 경로 주입 (`.env.example`에 명세 완료)
- 초기 실행 시 모델 다운로드 → 이후 볼륨 캐시 재사용

---

## 미결 사항 (추후 결정)

| 항목 | 현황 | 결정 필요 시점 |
|------|------|---------------|
| SlowFast 행동 인식 도입 | YOLOv8으로 1차 구현 후 평가 | 광고 파이프라인 1차 완성 후 |
| 이미지 생성 API 선택 | DALL-E 3 권장, 최종 미결 | 예산 확정 후 |
| 비디오 생성 API 선택 | RunwayML 또는 Kling | 예산 확정 후 |
| 한국어 형태소 분석기 | `konlpy.Okt` 또는 `kiwi` | nlp-api 구현 착수 시 |
| 서버 GPU 유무 확인 | 미확인 | 서버 접속 후 즉시 확인 |
| pgvector 도입 | schema_additions.sql 주석 처리 | VOD 풀 규모 파악 후 결정 |
