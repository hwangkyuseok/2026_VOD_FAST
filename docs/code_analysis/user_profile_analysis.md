# 📄 `user_profile.py` 소스코드 상세 분석

> **파일 경로**: `backend-api/app/models/user_profile.py`  
> **목적**: 유저의 NLP 추천 프로필 벡터를 데이터베이스 테이블과 연결하는 모델 클래스 정의  
> **분석일**: 2026-03-04

---

## 1. 이 파일이 하는 일 (전체 요약)

이 파일은 **"유저가 어떤 콘텐츠를 좋아하는지"** 를 담는 데이터 구조(테이블)를 정의합니다.

쉽게 말하면, PostgreSQL 데이터베이스에 있는 `tb_user_profile_vector` 테이블을 **Python 클래스로 표현**한 것입니다.  
이 방식을 **ORM (Object-Relational Mapping)** 이라고 하며, SQL을 직접 쓰는 대신 Python 코드로 DB를 다룰 수 있게 해줍니다.

```
유저 시청 데이터 → (분석) → UserProfileVector 테이블 → (조회) → NLP 추천 엔진
```

---

## 2. import 구문 분석 (1~8번째 줄)

```python
from datetime import datetime
from typing import Any, List

from sqlalchemy import String, Numeric, BigInteger, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
```

| import 항목 | 출처 | 역할 |
|---|---|---|
| `datetime` | Python 표준 라이브러리 | 날짜/시간 타입을 사용하기 위해 |
| `Any, List` | Python 표준 라이브러리 | 타입 힌트(어떤 타입인지 명시)에 사용 |
| `String, Numeric, BigInteger, func` | SQLAlchemy | DB 컬럼의 데이터 타입 지정에 사용 |
| `JSONB` | SQLAlchemy (PostgreSQL 전용) | 배열/딕셔너리를 DB에 저장하는 PostgreSQL 전용 타입 |
| `Mapped, mapped_column` | SQLAlchemy | Python 속성을 DB 컬럼과 연결하는 현대적인 방법 |
| `Base` | 우리 프로젝트 내부 (`app.core.db`) | 모든 DB 모델의 공통 부모 클래스 |

> **💡 초보자 팁**: `import`는 다른 파일/라이브러리에서 도구를 빌려오는 것입니다.  
> Python이 혼자 다 할 수 없기 때문에, 전문 도구(SQLAlchemy 등)를 불러씁니다.

---

## 3. 클래스 구조 분석

```python
class UserProfileVector(Base):
    """유저 NLP 추천 프로필 벡터."""
    __tablename__ = "tb_user_profile_vector"
    ...
```

### 3.1 클래스란?

`class`는 데이터와 기능을 하나로 묶는 **설계도**입니다.  
`UserProfileVector(Base)` 에서 `(Base)` 는 **"Base 클래스를 상속받는다"** 는 의미입니다.

```
Base (공통 DB 설정)
  └── UserProfileVector (tb_user_profile_vector 테이블 정의)
```

### 3.2 `__tablename__`

```python
__tablename__ = "tb_user_profile_vector"
```

이 Python 클래스가 데이터베이스의 **어느 테이블과 연결될지** 지정합니다.  
`tb_` 접두사는 "table"의 약자로, 테이블임을 명시하는 네이밍 컨벤션입니다.

---

## 4. 컬럼(필드) 상세 분석

### 4.1 `user_id` — 기본 키 (Primary Key)

```python
user_id: Mapped[str] = mapped_column(String(20), primary_key=True)
```

| 항목 | 설명 |
|---|---|
| **Python 타입** | `str` (문자열) |
| **DB 타입** | `String(20)` → 최대 20자 문자열 |
| **역할** | 테이블의 기본 키, 각 유저를 유일하게 식별 |
| **예시 값** | `"U20250001"` |

> **💡 기본 키(Primary Key)**: 테이블에서 각 행을 구분하는 유일한 식별자입니다.  
> 마치 학생의 학번처럼, 같은 값이 두 번 존재할 수 없습니다.

---

### 4.2 `profile_vector` — NLP 추천 벡터

```python
profile_vector: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
```

| 항목 | 설명 |
|---|---|
| **Python 타입** | `List[Any]` (어떤 타입이든 담을 수 있는 리스트) |
| **DB 타입** | `JSONB` (PostgreSQL의 이진 JSON 형식) |
| **예시 값** | `[0.12, -0.45, 0.88, ...]` (수백 개의 숫자) |

**무엇을 담나요?**  
NLP(자연어처리) 모델이 유저의 시청 이력을 분석해 만들어낸 **수치 벡터**입니다.  
이 벡터는 유저의 "취향 좌표"라고 볼 수 있으며, 비슷한 좌표를 가진 콘텐츠를 추천하는 데 사용됩니다.

```
시청 기록 → NLP 모델 → [0.12, -0.45, 0.88, ...] ← profile_vector
                                                         ↓
                                                 유사 콘텐츠 검색 → 추천
```

> **💡 `nullable=False`**: 이 컬럼은 반드시 값이 있어야 합니다 (NULL 불가).  
> **💡 `default=list`**: 값이 없으면 빈 리스트 `[]`를 기본값으로 씁니다.

---

### 4.3 `favorite_genres` — 선호 장르

```python
favorite_genres: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
```

| 항목 | 설명 |
|---|---|
| **DB 타입** | `JSONB` |
| **예시 값** | `["드라마", "예능", "스포츠"]` |

유저가 많이 시청한 **장르 목록**을 저장합니다.  
추천 알고리즘이 선호 장르를 점수 계산에 활용합니다.

---

### 4.4 `favorite_keywords` — 선호 키워드

```python
favorite_keywords: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
```

| 항목 | 설명 |
|---|---|
| **DB 타입** | `JSONB` |
| **예시 값** | `["로맨스", "범죄", "송중기", "tvN"]` |

유저가 좋아하는 **특정 키워드** (배우, 제작사, 주제 등)를 저장합니다.

---

### 4.5 `kids_boost_score` — 키즈 콘텐츠 가중치 ⭐ 비즈니스 핵심 필드

```python
# 비즈니스 룰: 최소 0.1 보장 (DB CHECK 제약 + 코드 양쪽에서 강제)
kids_boost_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.300)
```

| 항목 | 설명 |
|---|---|
| **Python 타입** | `float` (소수점 숫자) |
| **DB 타입** | `Numeric(4, 3)` → 전체 4자리, 소수점 이하 3자리 |
| **범위** | `0.100` ~ `1.000` (최소 0.1 보장) |
| **기본값** | `0.300` (30%) |

**무엇을 하나요?**  
유저에게 키즈 콘텐츠를 얼마나 강조할지 결정하는 **가중치 점수**입니다.

```
kids_boost_score = 0.1 → 키즈 콘텐츠 거의 노출 안 함 (성인 유저)
kids_boost_score = 0.8 → 키즈 콘텐츠 많이 노출 (어린이가 있는 가정)
```

> **⚠️ 주석의 의미**: `비즈니스 룰: 최소 0.1 보장`  
> 이 규칙은 **DB 제약조건** (CHECK constraint)과 **애플리케이션 코드**, 두 곳에서 동시에 강제됩니다.  
> 이중으로 검증하는 이유는 데이터 무결성을 확실히 보장하기 위해서입니다.

> **💡 `Numeric(4, 3)` 설명**:  
> `4`는 전체 자릿수, `3`은 소수점 이하 자릿수입니다.  
> 즉 `1.000`과 같이 정수 1자리 + 소수 3자리로 표현됩니다.

---

### 4.6 `recent_genres` — 최근 시청 장르

```python
recent_genres: Mapped[List[Any]] = mapped_column(JSONB, nullable=False, default=list)
```

| 항목 | 설명 |
|---|---|
| **DB 타입** | `JSONB` |
| **예시 값** | `["드라마", "드라마", "예능"]` |

`favorite_genres`와 달리, **최근에 시청한 장르**를 순서대로 담습니다.  
최신 취향 변화를 반영하는 데 사용됩니다.

---

### 4.7 `total_watch_sec` — 총 시청 시간 (초)

```python
total_watch_sec: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
```

| 항목 | 설명 |
|---|---|
| **Python 타입** | `int` (정수) |
| **DB 타입** | `BigInteger` (매우 큰 정수, 최대 약 922경) |
| **단위** | 초(seconds) |
| **예시 값** | `86400` (1일 = 24시간 × 60분 × 60초) |

> **💡 왜 `BigInteger`?**  
> 장기 사용자는 총 시청 시간이 수백만 초에 달할 수 있습니다.  
> 일반 `Integer`의 최대값(약 21억)을 초과할 수 있어, 더 큰 `BigInteger`를 사용합니다.

---

### 4.8 `created_at` / `updated_at` — 타임스탬프

```python
created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
```

| 컬럼 | 설명 |
|---|---|
| `created_at` | 레코드가 처음 생성된 시각 |
| `updated_at` | 레코드가 마지막으로 수정된 시각 |

> **💡 `server_default=func.now()`**:  
> DB 서버의 현재 시간(`NOW()` SQL 함수)을 기본값으로 사용합니다.  
> Python 코드에서 시간을 별도로 넣어주지 않아도, DB가 자동으로 채워줍니다.

---

## 5. 전체 테이블 구조 요약

```
tb_user_profile_vector
─────────────────────────────────────────────────────────────────
컬럼명               | DB 타입          | 설명
─────────────────────────────────────────────────────────────────
user_id (PK)        | VARCHAR(20)      | 유저 고유 ID (기본 키)
profile_vector      | JSONB            | NLP 추천 벡터 (숫자 배열)
favorite_genres     | JSONB            | 선호 장르 목록
favorite_keywords   | JSONB            | 선호 키워드 목록
kids_boost_score    | NUMERIC(4,3)     | 키즈 콘텐츠 가중치 (0.1~1.0)
recent_genres       | JSONB            | 최근 시청 장르
total_watch_sec     | BIGINT           | 누적 시청 시간 (초)
created_at          | TIMESTAMP        | 생성 시각 (자동)
updated_at          | TIMESTAMP        | 수정 시각 (자동)
─────────────────────────────────────────────────────────────────
```

---

## 6. 아키텍처 관점에서의 역할

```
[시청 데이터 수집]
      ↓
[배치 파이프라인 / NLP 분석]
      ↓
[UserProfileVector 갱신] ← 이 파일이 정의하는 테이블
      ↓
[추천 API 요청]
      ↓
[profile_vector, favorite_genres, kids_boost_score 조회]
      ↓
[추천 결과 반환]
```

이 모델은 **콜드 스타트 시나리오**에서도 중요합니다.  
신규 유저는 `profile_vector`가 빈 배열(`[]`)이므로, 추천 엔진이 이를 감지해 인기 콘텐츠 기반 추천으로 폴백(fallback)합니다.

---

## 7. SQLAlchemy 현대적 문법 (`Mapped`) 설명

이 파일은 SQLAlchemy **2.0 스타일**의 선언적 매핑을 사용합니다.

```python
# 구식 방법 (SQLAlchemy 1.x)
user_id = Column(String(20), primary_key=True)

# 현대적 방법 (SQLAlchemy 2.x) ← 이 파일에서 사용
user_id: Mapped[str] = mapped_column(String(20), primary_key=True)
```

`Mapped[str]`은 **타입 힌트**를 통해 IDE(코드 에디터)가 자동완성과 오류 감지를 더 잘 할 수 있도록 돕습니다.

---

## 8. 요약 및 핵심 포인트

| 포인트 | 내용 |
|---|---|
| **파일 역할** | PostgreSQL `tb_user_profile_vector` 테이블을 Python 클래스로 표현 |
| **ORM** | SQLAlchemy 2.x 스타일 사용 |
| **핵심 데이터** | NLP 벡터, 선호 장르/키워드, 키즈 가중치 |
| **주목할 점** | `kids_boost_score`의 최소값 0.1 규칙 (DB + 코드 이중 강제) |
| **자동화** | `created_at`, `updated_at`은 DB 서버가 자동으로 채움 |
| **확장성** | `BigInteger`로 장기 시청 데이터도 안전하게 저장 |

---

*분석 완료 — `user_profile.py` (25 lines)*
