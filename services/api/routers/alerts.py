"""
Alerts router — create/list/delete price & indicator alerts.
Notification delivery runs via the scheduler cron.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

from core.database import get_db
from routers.auth import get_current_user
from models.models import User, Alert, Notification, AlertConditionEnum, ExchangeEnum

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class CreateAlertRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    condition: AlertConditionEnum
    threshold_value: Optional[float] = None

class AlertOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    condition: str
    threshold_value: Optional[float] = None
    is_active: bool
    model_config = {"from_attributes": True}

class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    related_symbol: Optional[str] = None
    is_read: bool
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Alert CRUD
# ─────────────────────────────────────────────

@router.get("", response_model=List[AlertOut])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.user_id == current_user.id, Alert.is_active == True)
    )
    return [AlertOut.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=AlertOut, status_code=201)
async def create_alert(
    req: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    alert = Alert(
        user_id=current_user.id,
        symbol=req.symbol.upper(),
        exchange=ExchangeEnum(req.exchange),
        condition=req.condition,
        threshold_value=Decimal(str(req.threshold_value)) if req.threshold_value else None,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return AlertOut.model_validate(alert)


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_active = False  # Soft delete
    await db.commit()


# ─────────────────────────────────────────────
# Notifications
# ─────────────────────────────────────────────

@router.get("/notifications", response_model=List[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


@router.post("/notifications/{notification_id}/read", status_code=200)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()
    return {"status": "read"}
