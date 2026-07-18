from fastapi import APIRouter, Query
from app.services.alpha_service import alpha_service

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("/whale-accumulation")
async def whale_accumulation(
    min_change_pct: float = Query(20.0, ge=5, le=100, description="Min volume/mcap % threshold"),
):
    """Detect potential whale accumulation: high volume relative to market cap with positive price action."""
    return await alpha_service.get_whale_accumulation(min_change_pct=min_change_pct)


@router.get("/volume-anomaly")
async def volume_anomaly(
    min_volume_ratio: float = Query(3.0, ge=1, le=50, description="Min volume/mcap ratio (%)"),
):
    """Find coins with unusual volume spikes (potential breakouts or sell-offs)."""
    return await alpha_service.get_volume_anomalies(min_volume_ratio=min_volume_ratio)


@router.get("/momentum")
async def momentum_signals(
    coin_id: str = Query("bitcoin", description="Coin ID (e.g. bitcoin, ethereum, solana)"),
    days: int = Query(30, ge=7, le=365, description="Days of price history for analysis"),
):
    """Technical analysis signals: RSI, MACD, Bollinger Bands, Stochastic, VWAP with overall buy/sell bias."""
    result = await alpha_service.get_momentum_signals(coin_id=coin_id, days=days)
    if "error" in result:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=result["error"])
    return result
