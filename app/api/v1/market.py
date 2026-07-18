from fastapi import APIRouter, Query, HTTPException
from app.services.market_service import market_service
from app.services.sentiment_service import sentiment_service
from app.services.chains import CHAIN_TOKEN_MAP

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/top")
async def get_top_coins(
    limit: int = Query(20, ge=1, le=250, description="Number of coins to return"),
    currency: str = Query("usd", description="Fiat currency (usd, eur, gbp, jpy)"),
):
    """Get top cryptocurrencies ranked by market cap."""
    return await market_service.get_top_coins(limit=limit, currency=currency)


@router.get("/coin/{coin_id}")
async def get_coin_detail(
    coin_id: str,
    currency: str = Query("usd", description="Fiat currency"),
):
    """Get detailed data for a single coin (price, market cap, volume, description, links)."""
    result = await market_service.get_coin_detail(coin_id=coin_id, currency=currency)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Coin not found")
    return result


@router.get("/coins")
async def get_coins_bulk(
    ids: str = Query(..., description="Comma-separated coin IDs (e.g. 'bitcoin,ethereum,solana')"),
    currency: str = Query("usd", description="Fiat currency"),
):
    """Get current prices and basic data for multiple coins at once."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="At least one coin ID required")
    return await market_service.get_coins_bulk(ids=id_list, currency=currency)


@router.get("/compare")
async def compare_coins(
    coin1: str = Query(..., description="First coin ID (e.g. 'bitcoin')"),
    coin2: str = Query(..., description="Second coin ID (e.g. 'ethereum')"),
    currency: str = Query("usd", description="Fiat currency"),
):
    """Compare two coins side by side: price, market cap, volume, price changes."""
    result = await market_service.compare_coins(coin1=coin1, coin2=coin2, currency=currency)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/trending")
async def get_trending():
    """Get trending coins in the last 24 hours (by search volume)."""
    return await market_service.get_trending()


@router.get("/global")
async def get_global_data():
    """Get global crypto market stats: total market cap, volume, BTC dominance, active coins."""
    return await market_service.get_global_data()


@router.get("/search")
async def search_coins(query: str = Query(..., min_length=1, description="Search query (e.g. 'solana')")):
    """Search for coins by name or symbol."""
    return await market_service.search_coins(query=query)


@router.get("/history")
async def get_price_history(
    coin_id: str = Query(..., description="Coin ID (e.g. 'bitcoin')"),
    days: int = Query(30, ge=1, le=365, description="Number of days of price history"),
    currency: str = Query("usd", description="Fiat currency"),
):
    """Get historical daily prices for a coin (used for charts and analysis)."""
    result = await market_service.get_price_history(coin_id=coin_id, days=days, currency=currency)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/correlation")
async def get_correlation(
    ids: str = Query(..., description="Comma-separated asset IDs (e.g. 'bitcoin,ethereum,s&p500')"),
    days: int = Query(30, ge=7, le=365, description="Days of history for correlation calculation"),
    currency: str = Query("usd", description="Fiat currency"),
):
    """Calculate price correlation matrix between up to 5 assets."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 assets required for correlation")
    if len(id_list) > 5:
        raise HTTPException(status_code=400, detail="Max 5 assets")
    result = await market_service.get_correlation(coin_ids=id_list, days=days, vs_currency=currency)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/fear-greed")
async def get_fear_greed_index():
    """Get current Fear & Greed Index (0-100) with classification."""
    return await sentiment_service.get_fear_greed_index()


@router.get("/fear-greed/history")
async def get_fear_greed_history(limit: int = Query(30, ge=1, le=365, description="Number of days of history")):
    """Get historical Fear & Greed Index values."""
    return await sentiment_service.get_fear_greed_history(limit=limit)


@router.get("/chain/{chain}/tokens")
async def get_chain_tokens(
    chain: str,
    currency: str = Query("usd", description="Fiat currency"),
):
    """Get top tokens on a specific blockchain (ethereum, bsc, polygon, etc.)."""
    if chain not in CHAIN_TOKEN_MAP:
        raise HTTPException(status_code=400, detail=f"Chain '{chain}' not supported. Use: {list(CHAIN_TOKEN_MAP.keys())}")
    token_ids = list(CHAIN_TOKEN_MAP[chain].values())
    return await market_service.get_coins_bulk(ids=token_ids, currency=currency)
