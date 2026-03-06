import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.session import WatchSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionStartRequest(BaseModel):
    user_id: str
    session_type: str  # CHANNEL | VOD_TRACK1 | VOD_TRACK2
    channel_no: Optional[int] = None
    asset_id: Optional[str] = None


class SessionEndRequest(BaseModel):
    watch_sec: Optional[int] = None
    ad_impression_count: int = 0
    shopping_click_count: int = 0


class SessionOut(BaseModel):
    session_id: uuid.UUID
    user_id: str
    session_type: str
    channel_no: Optional[int] = None
    asset_id: Optional[str] = None
    start_dt: datetime

    model_config = {"from_attributes": True}


@router.post("/start", response_model=SessionOut, status_code=201)
async def start_session(req: SessionStartRequest, db: AsyncSession = Depends(get_db)):
    """시청 세션 시작."""
    session = WatchSession(
        user_id=req.user_id,
        session_type=req.session_type,
        channel_no=req.channel_no,
        asset_id=req.asset_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.patch("/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: uuid.UUID,
    req: SessionEndRequest,
    db: AsyncSession = Depends(get_db),
):
    """시청 세션 종료."""
    from fastapi import HTTPException
    from sqlalchemy import select

    result = await db.execute(
        select(WatchSession).where(WatchSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    session.end_dt = datetime.utcnow()
    session.watch_sec = req.watch_sec
    session.ad_impression_count = req.ad_impression_count
    session.shopping_click_count = req.shopping_click_count

    await db.commit()
    await db.refresh(session)
    return session
