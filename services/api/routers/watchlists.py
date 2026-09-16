"""
Watchlists router — CRUD for user watchlists + items.
All endpoints require authentication.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from routers.auth import get_current_user
from models.models import User, Watchlist, WatchlistItem, ExchangeEnum

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class WatchlistItemOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    model_config = {"from_attributes": True}

class WatchlistOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items: List[WatchlistItemOut] = []
    model_config = {"from_attributes": True}

class CreateWatchlistRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AddWatchlistItemRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.get("", response_model=List[WatchlistOut])
async def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all watchlists for the current user with their items."""
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id)
    )
    watchlists = result.scalars().all()

    out = []
    for wl in watchlists:
        items_result = await db.execute(
            select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
        )
        items = items_result.scalars().all()
        out.append(WatchlistOut(
            id=wl.id,
            name=wl.name,
            description=wl.description,
            items=[WatchlistItemOut.model_validate(i) for i in items],
        ))
    return out


@router.post("", response_model=WatchlistOut, status_code=201)
async def create_watchlist(
    req: CreateWatchlistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new watchlist."""
    wl = Watchlist(user_id=current_user.id, name=req.name, description=req.description)
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    return WatchlistOut(id=wl.id, name=wl.name, description=wl.description, items=[])


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a watchlist and all its items."""
    result = await db.execute(
        select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id)
    )
    wl = result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    # Delete items first
    await db.execute(delete(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id))
    await db.delete(wl)
    await db.commit()


@router.post("/{watchlist_id}/items", response_model=WatchlistItemOut, status_code=201)
async def add_to_watchlist(
    watchlist_id: int,
    req: AddWatchlistItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a stock to a watchlist."""
    # Verify ownership
    result = await db.execute(
        select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Watchlist not found")

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        symbol=req.symbol.upper(),
        exchange=ExchangeEnum(req.exchange),
    )
    db.add(item)
    try:
        await db.commit()
        await db.refresh(item)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    return WatchlistItemOut.model_validate(item)


@router.delete("/{watchlist_id}/items/{item_id}", status_code=204)
async def remove_from_watchlist(
    watchlist_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a stock from a watchlist."""
    result = await db.execute(
        select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Watchlist not found")

    item_result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.id == item_id, WatchlistItem.watchlist_id == watchlist_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
