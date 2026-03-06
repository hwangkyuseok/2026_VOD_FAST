from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(prefix="/shopping", tags=["shopping"])


class ProductOut(BaseModel):
    prod_cd: str
    prod_nm: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    thumbnail_url: Optional[str] = None
    match_score: Optional[float] = None


@router.get("/match", response_model=List[ProductOut])
async def match_products(
    keywords: str = Query(..., description="쉼표 구분 키워드 (비전 AI 추출값)"),
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
):
    """키워드 기반 상품 매칭 (쇼핑 오버레이용)."""
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not kw_list:
        return []

    # ILIKE 다중 조건 (간단한 텍스트 매칭)
    conditions = " OR ".join([
        f"(PROD_NM ILIKE :kw{i} OR CATEGORY ILIKE :kw{i})"
        for i in range(len(kw_list))
    ])
    params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(kw_list)}
    params["limit"] = limit

    result = await db.execute(
        text(f"""
            SELECT PROD_CD, PROD_NM, CATEGORY, PRICE, THUMBNAIL_URL
            FROM TB_PROD_INFO
            WHERE ({conditions})
            ORDER BY PRICE
            LIMIT :limit
        """),
        params,
    )
    rows = result.mappings().all()
    return [
        ProductOut(
            prod_cd=r["PROD_CD"],
            prod_nm=r.get("PROD_NM"),
            category=r.get("CATEGORY"),
            price=float(r["PRICE"]) if r.get("PRICE") else None,
            thumbnail_url=r.get("THUMBNAIL_URL"),
        )
        for r in rows
    ]


@router.get("/products", response_model=List[ProductOut])
async def list_products(
    category: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """상품 목록 조회."""
    if category:
        result = await db.execute(
            text("SELECT PROD_CD, PROD_NM, CATEGORY, PRICE, THUMBNAIL_URL FROM TB_PROD_INFO WHERE CATEGORY ILIKE :cat ORDER BY SRL_NO LIMIT :limit OFFSET :offset"),
            {"cat": f"%{category}%", "limit": limit, "offset": offset},
        )
    else:
        result = await db.execute(
            text("SELECT PROD_CD, PROD_NM, CATEGORY, PRICE, THUMBNAIL_URL FROM TB_PROD_INFO ORDER BY SRL_NO LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        )
    rows = result.mappings().all()
    return [
        ProductOut(
            prod_cd=r["PROD_CD"],
            prod_nm=r.get("PROD_NM"),
            category=r.get("CATEGORY"),
            price=float(r["PRICE"]) if r.get("PRICE") else None,
            thumbnail_url=r.get("THUMBNAIL_URL"),
        )
        for r in rows
    ]
