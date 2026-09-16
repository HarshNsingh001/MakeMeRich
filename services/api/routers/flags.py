"""
Feature Flags admin router — view and toggle flags at runtime.
Endpoints are protected and intended for internal/ops use.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.feature_flags import get_all_flags, set_flag, is_enabled
from routers.auth import get_current_user
from models.models import User

router = APIRouter(prefix="/admin/flags", tags=["admin"])


class SetFlagRequest(BaseModel):
    enabled: bool
    rollout_pct: int = 100
    description: Optional[str] = None


@router.get("")
async def list_flags(current_user: User = Depends(get_current_user)):
    """List all feature flags with their current values."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    return await get_all_flags()


@router.put("/{flag_name}")
async def update_flag(
    flag_name: str,
    req: SetFlagRequest,
    current_user: User = Depends(get_current_user),
):
    """Toggle a feature flag at runtime."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin only")
    result = await set_flag(
        flag_name=flag_name,
        enabled=req.enabled,
        rollout_pct=req.rollout_pct,
        description=req.description or "",
    )
    return result


@router.get("/{flag_name}/check")
async def check_flag(flag_name: str):
    """Public endpoint to check if a specific flag is enabled (no auth needed)."""
    value = await is_enabled(flag_name)
    return {"flag": flag_name, "enabled": value}
