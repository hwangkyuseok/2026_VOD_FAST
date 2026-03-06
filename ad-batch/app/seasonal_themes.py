"""월별 시즌 테마 키워드 관리 모듈 (ad-batch/app/seasonal_themes.py).

SQL CASE-WHEN 구문을 동적으로 생성하여 main.py 내 CTE 쿼리에 주입합니다.
테마 키워드를 수정하려면 SEASONAL_THEMES 딕셔너리만 업데이트하면 됩니다.
"""

# 월별 시즌 테마 (키: 월, 값: [SMRY/TTL 검색 키워드 목록])
SEASONAL_THEMES: dict[int, list[str]] = {
    1:  ["새해", "겨울", "설날", "신년"],
    2:  ["설날", "명절", "가족", "한복"],
    3:  ["봄", "벚꽃", "새학기", "입학"],
    4:  ["여행", "봄", "꽃구경", "나들이"],
    5:  ["어린이", "가족", "효도", "엄마", "아빠"],
    6:  ["여름", "축구", "스포츠", "야구"],
    7:  ["여름", "바다", "휴가", "피서"],
    8:  ["독립", "광복", "역사", "바다"],
    9:  ["추석", "명절", "가을", "단풍", "풍성한"],
    10: ["가을", "단풍", "공포", "미스터리"],
    11: ["청춘", "학교", "도전", "가을"],
    12: ["크리스마스", "연말", "겨울", "산타"],
}

# 슬롯 그룹 → SELECTION_REASON 매핑
SLOT_REASON_MAP: dict[str, str] = {
    "KIDS":          "SLOT_KIDS",
    "DOCU_LIFE":     "SLOT_DOCU",
    "ENTERTAINMENT": "SLOT_ENT",
    "ETC":           "SLOT_ETC",
}


def build_seasonal_case_when() -> str:
    """현재 월 기준 시즌 보너스 SQL CASE-WHEN 절을 동적으로 생성합니다.

    반환값은 `SELECT` 절의 계산식 일부로 직접 삽입됩니다.
    PostgreSQL 정규식(`~`) 연산자를 사용합니다.

    Returns:
        str: CASE WHEN ... ELSE 0 END 형태의 SQL 스니펫
    """
    cases: list[str] = []
    for month, keywords in SEASONAL_THEMES.items():
        pattern = "|".join(keywords)
        cases.append(
            f"            WHEN EXTRACT(MONTH FROM CURRENT_DATE) = {month}\n"
            f"                 AND (SMRY ~ '({pattern})' OR TTL ~ '({pattern})') THEN 30"
        )
    case_block = "\n".join(cases)
    return f"        (CASE\n{case_block}\n            ELSE 0\n        END)"
