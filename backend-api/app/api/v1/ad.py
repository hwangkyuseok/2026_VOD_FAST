from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.ad import FastAdInsertionPoint, FastAdAsset

router = APIRouter(prefix="/ad", tags=["ad"])


class InsertionPointOut(BaseModel):
    timestamp_sec: float
    confidence: float
    insert_reason: Optional[str] = None
    display_duration_sec: float
    display_position: str
    ad_type: Optional[str] = None
    file_path: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/insertion-points/{asset_id}", response_model=List[InsertionPointOut])
async def get_insertion_points(
    asset_id: str,
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """VOD의 광고 삽입 타임스탬프 목록 (신뢰도 필터 적용)."""
    result = await db.execute(
        select(FastAdInsertionPoint, FastAdAsset)
        .join(FastAdAsset, FastAdInsertionPoint.ad_asset_uid == FastAdAsset.asset_uid)
        .where(FastAdInsertionPoint.vod_asset_id == asset_id)
        .where(FastAdInsertionPoint.is_active == "Y")
        .where(FastAdInsertionPoint.confidence >= min_confidence)
        .order_by(FastAdInsertionPoint.timestamp_sec)
    )
    rows = result.all()

    return [
        InsertionPointOut(
            timestamp_sec=float(ip.timestamp_sec),
            confidence=float(ip.confidence),
            insert_reason=ip.insert_reason,
            display_duration_sec=float(ip.display_duration_sec),
            display_position=ip.display_position,
            ad_type=asset.ad_type,
            file_path=asset.file_path,
        )
        for ip, asset in rows
    ]
