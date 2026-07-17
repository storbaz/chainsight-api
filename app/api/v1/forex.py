from fastapi import APIRouter, Query, HTTPException
from app.services.forex_service import forex_service

router = APIRouter(prefix="/forex", tags=["Forex & Markets"])


@router.get("/rates")
async def get_rates(
    base: str = Query("EUR", description="Base currency"),
    symbols: str = Query("", description="Comma-separated target currencies"),
):
    return await forex_service.get_latest_rates(base=base, symbols=symbols)


@router.get("/pairs")
async def get_pairs_overview():
    return await forex_service.get_pairs_overview()


@router.get("/history")
async def get_pair_history(
    symbol: str = Query(..., description="Pair symbol (e.g. EUR/USD, AAPL, GC=F)"),
    range: str = Query("1mo", description="Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y"),
    interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
):
    result = await forex_service.get_pair_history(symbol=symbol, range_=range, interval=interval)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/overview")
async def get_market_overview():
    return await forex_service.get_market_overview()


@router.get("/search")
async def search_pairs(query: str = Query(..., min_length=1)):
    return await forex_service.search_pairs(query=query)


@router.get("/major")
async def get_major_forex():
    result = await forex_service.get_pairs_overview()
    forex_only = [p for p in result.get("pairs", []) if p.get("type") == "forex"]
    return {"pairs": forex_only, "total": len(forex_only)}
