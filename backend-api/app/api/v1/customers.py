from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerOut(BaseModel):
    user_id: str
    cust_nm: Optional[str] = None
    service_type: Optional[str] = None
    join_dt: Optional[str] = None


@router.get("/{user_id}", response_model=CustomerOut)
async def get_customer(user_id: str, db: AsyncSession = Depends(get_db)):
    """고객 정보 조회 (TB_CUST_INFO)."""
    result = await db.execute(
        text("SELECT USER_ID, CUST_NM, SERVICE_TYPE, JOIN_DT FROM TB_CUST_INFO WHERE USER_ID = :uid LIMIT 1"),
        {"uid": user_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=f"고객 {user_id}를 찾을 수 없습니다.")
    return CustomerOut(
        user_id=row["USER_ID"],
        cust_nm=row.get("CUST_NM"),
        service_type=row.get("SERVICE_TYPE"),
        join_dt=row.get("JOIN_DT"),
    )
