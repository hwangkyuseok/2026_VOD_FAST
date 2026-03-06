"""0번 채널 (TV Commerce) 데이터 API.

2026_TV_COMMERCE 프로젝트의 /api/v1/data 엔드포인트를 2026_TV에 통합.
메뉴와 추천채널은 고정값, 상품은 TB_PROD_INFO에서 실시간 조회.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(prefix="/commerce", tags=["commerce"])

# ── 고정 메뉴 및 추천 채널 ─────────────────────────────────────────────────
FIXED_MENUS = ["실시간 추천 채널", "VOD", "키즈", "영화", "스포츠", "쇼핑", "약정"]

FIXED_RECOMMENDED_CHANNELS = [
    {"id": "ch_drama", "title": "HV 드라마 (추천)", "desc": "드라마 · 예능", "badge": "LIVE", "bg": "#2d1a4a"},
    {"id": "ch_news",  "title": "HV 뉴스 (추천)",   "desc": "뉴스 · 생활경제", "badge": "LIVE", "bg": "#1a2d4a"},
    {"id": "ch_kids",  "title": "HV 키즈 (추천)",   "desc": "키즈 · 애니",   "badge": "LIVE", "bg": "#1a4a2e"},
]


class RecommendedChannel(BaseModel):
    id: str
    title: str
    desc: str
    badge: str
    bg: str


class CommerceProduct(BaseModel):
    id: str
    name: str
    price: int
    thumbnail_url: Optional[str] = None
    is_rental: bool = False
    category: Optional[str] = None


class CommerceData(BaseModel):
    menus: List[str]
    recommendedChannels: List[RecommendedChannel]
    products: List[CommerceProduct]


@router.get("/data", response_model=CommerceData)
async def get_commerce_data(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """0번 채널 TV Commerce 화면 데이터 반환.

    - menus: 사이드바 메뉴 고정값
    - recommendedChannels: 추천 채널 고정값 (실제 채널 DB로 확장 가능)
    - products: TB_PROD_INFO에서 상품 조회 (가격 기준 정렬)
    """
    result = await db.execute(
        text("""
            SELECT
                srl_no,
                prod_cd,
                prod_nm,
                COALESCE(sale_price, monthly_rental_fee) AS price,
                thumbnail_url,
                category,
                brand,
                is_rental
            FROM tb_prod_info
            WHERE prod_nm IS NOT NULL
            ORDER BY srl_no
            LIMIT :limit
        """),
        {"limit": limit},
    )
    rows = result.mappings().all()

    products = [
        CommerceProduct(
            id=str(r["prod_cd"]),
            name=r.get("prod_nm") or "상품명 없음",
            price=int(r["price"]) if r.get("price") else 0,
            thumbnail_url=r.get("thumbnail_url"),
            is_rental=(r.get("is_rental") or "N").strip().upper() == "Y",
            category=r.get("category"),
        )
        for r in rows
    ]

    return CommerceData(
        menus=FIXED_MENUS,
        recommendedChannels=[RecommendedChannel(**ch) for ch in FIXED_RECOMMENDED_CHANNELS],
        products=products,
    )
