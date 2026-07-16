from fastapi import APIRouter, Query
from app.services.alpha_service import alpha_service

router = APIRouter(prefix="/signals", tags=["Alpha Signals"])


@router.get("/whale-accumulation")
async def whale_accumulation(
    min_change_pct: float = Query(20.0, description="Min volume/mcap % threshold"),
):
    return await alpha_service.get_whale_accumulation(min_change_pct=min_change_pct)


@router.get("/volume-anomaly")
async def volume_anomaly(
    min_volume_ratio: float = Query(3.0, description="Min volume/mcap ratio"),
):
    return await alpha_service.get_volume_anomalies(min_volume_ratio=min_volume_ratio)


@router.get("/momentum")
async def momentum_signals(
    coin_id: str = Query("bitcoin", description="Coin ID (e.g. bitcoin, ethereum)"),
    days: int = Query(30, ge=7, le=365, description="Days of history"),
):
    result = await alpha_service.get_momentum_signals(coin_id=coin_id, days=days)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result["error"])
    return result
