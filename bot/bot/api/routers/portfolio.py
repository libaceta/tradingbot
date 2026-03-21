from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.dependencies import get_db
from bot.db.repositories.portfolio_repo import get_snapshots, get_latest_snapshot

router = APIRouter()


@router.get("/portfolio/current")
async def get_current_portfolio(db: AsyncSession = Depends(get_db)):
    snap = await get_latest_snapshot(db)
    if not snap:
        return {
            "equity_usdt": 0,
            "available_usdt": 0,
            "unrealized_pnl": 0,
            "open_positions": 0,
            "drawdown_pct": 0,
            "peak_equity": 0,
        }
    return {
        "equity_usdt": float(snap.equity_usdt),
        "available_usdt": float(snap.available_usdt),
        "unrealized_pnl": float(snap.unrealized_pnl or 0),
        "open_positions": snap.open_positions or 0,
        "drawdown_pct": float(snap.drawdown_pct or 0),
        "peak_equity": float(snap.peak_equity or snap.equity_usdt),
        "snapshot_time": snap.snapshot_time.isoformat(),
    }


@router.get("/portfolio/equity-curve")
async def get_equity_curve(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    snaps = await get_snapshots(db, date_from=date_from, date_to=date_to)
    return [
        {"time": int(s.snapshot_time.timestamp() * 1000), "value": float(s.equity_usdt)}
        for s in snaps
    ]


@router.get("/portfolio/drawdown")
async def get_drawdown(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    snaps = await get_snapshots(db, date_from=date_from, date_to=date_to)
    return [
        {
            "time": int(s.snapshot_time.timestamp() * 1000),
            "value": -float(s.drawdown_pct or 0),
        }
        for s in snaps
    ]


@router.get("/portfolio/monthly-returns")
async def get_monthly_returns(
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import timezone
    date_from = None
    date_to = None
    if year:
        date_from = datetime(year, 1, 1, tzinfo=timezone.utc)
        date_to = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    snaps = await get_snapshots(db, date_from=date_from, date_to=date_to, limit=50000)
    if not snaps:
        return {}

    import pandas as pd
    df = pd.DataFrame([
        {"time": s.snapshot_time, "equity": float(s.equity_usdt)}
        for s in snaps
    ])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()

    monthly = df["equity"].resample("ME").last().ffill()
    pct = monthly.pct_change() * 100

    return {str(dt.strftime("%Y-%m")): round(float(v), 4) for dt, v in pct.items() if not pd.isna(v)}
