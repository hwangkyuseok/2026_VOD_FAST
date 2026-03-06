from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.vod import VodMeta, WeeklyFreeVod

router = APIRouter(prefix="/vod", tags=["vod"])


class VodMetaOut(BaseModel):
    asset_id: str
    title: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_sec: Optional[int] = None
    rating: Optional[float] = None
    view_count: Optional[int] = None
    is_free_yn: str
    fast_ad_eligible_yn: str

    model_config = {"from_attributes": True}


class WeeklyVodOut(BaseModel):
    rank_no: int
    asset_id: str
    week_start_ymd: str
    selection_score: Optional[float] = None
    selection_reason: Optional[str] = None
    ad_pipeline_status: str
    title: Optional[str] = None
    genre: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_sec: Optional[int] = None

    model_config = {"from_attributes": True}


def _current_week_start() -> str:
    """현재 주의 월요일 날짜를 YYYYMMDD 형식으로 반환."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y%m%d")


@router.get("/weekly", response_model=List[WeeklyVodOut])
async def get_weekly_free_vod(
    week: Optional[str] = Query(None, description="YYYYMMDD 형식 (기본: 현재 주)"),
    db: AsyncSession = Depends(get_db),
):
    """금주의 무료 VOD 목록 조회 (트랙 1)."""
    week_start = week or _current_week_start()

    result = await db.execute(
        select(WeeklyFreeVod, VodMeta)
        .join(VodMeta, WeeklyFreeVod.asset_id == VodMeta.asset_id)
        .where(WeeklyFreeVod.week_start_ymd == week_start)
        .where(WeeklyFreeVod.is_active == "Y")
        .order_by(WeeklyFreeVod.rank_no)
    )
    rows = result.all()

    out = []
    for wv, vm in rows:
        out.append(WeeklyVodOut(
            rank_no=wv.rank_no,
            asset_id=wv.asset_id,
            week_start_ymd=wv.week_start_ymd,
            selection_score=float(wv.selection_score) if wv.selection_score else None,
            selection_reason=wv.selection_reason,
            ad_pipeline_status=wv.ad_pipeline_status,
            title=vm.title,
            genre=vm.genre,
            thumbnail_url=vm.thumbnail_url,
            duration_sec=vm.duration_sec,
        ))
    return out


@router.get("/free", response_model=List[VodMetaOut])
async def list_free_vod(
    genre: Optional[str] = Query(None, description="장르 필터"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """무료 VOD 목록 조회 (트랙 2 후보 풀)."""
    q = select(VodMeta).where(VodMeta.is_free_yn == "Y")
    if genre:
        q = q.where(VodMeta.genre.ilike(f"%{genre}%"))
    q = q.order_by(VodMeta.view_count.desc()).limit(limit).offset(offset)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{asset_id}", response_model=VodMetaOut)
async def get_vod(asset_id: str, db: AsyncSession = Depends(get_db)):
    """VOD 상세 조회."""
    from fastapi import HTTPException
    result = await db.execute(select(VodMeta).where(VodMeta.asset_id == asset_id))
    vod = result.scalar_one_or_none()
    if not vod:
        raise HTTPException(status_code=404, detail=f"VOD {asset_id}를 찾을 수 없습니다.")
    return vod
