from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.channel import ChannelConfig

router = APIRouter(prefix="/channels", tags=["channels"])


class ChannelOut(BaseModel):
    channel_no: int
    channel_nm: str
    category: str
    stream_url: Optional[str] = None
    logo_url: Optional[str] = None
    current_asset_id: Optional[str] = None
    channel_color: str
    is_active: str
    sort_order: int

    model_config = {"from_attributes": True}


@router.get("", response_model=List[ChannelOut])
async def list_channels(db: AsyncSession = Depends(get_db)):
    """활성 채널 목록 조회 (정렬 순서 기준)."""
    result = await db.execute(
        select(ChannelConfig)
        .where(ChannelConfig.is_active == "Y")
        .order_by(ChannelConfig.sort_order)
    )
    return result.scalars().all()


@router.get("/{channel_no}", response_model=ChannelOut)
async def get_channel(channel_no: int, db: AsyncSession = Depends(get_db)):
    """특정 채널 정보 조회."""
    result = await db.execute(
        select(ChannelConfig).where(ChannelConfig.channel_no == channel_no)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail=f"채널 {channel_no}를 찾을 수 없습니다.")
    return ch


@router.put("/{channel_no}/stream", response_model=ChannelOut)
async def update_channel_stream(
    channel_no: int,
    stream_url: str,
    db: AsyncSession = Depends(get_db),
):
    """채널 스트림 URL 업데이트."""
    result = await db.execute(
        select(ChannelConfig).where(ChannelConfig.channel_no == channel_no)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404, detail=f"채널 {channel_no}를 찾을 수 없습니다.")
    ch.stream_url = stream_url
    await db.commit()
    await db.refresh(ch)
    return ch
