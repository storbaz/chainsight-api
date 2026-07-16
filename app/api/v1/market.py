from fastapi import APIRouter, Query, HTTPException
from app.services.market_service import market_service
from app.services.sentiment_service import sentiment_service

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/top")
async def get_top_coins(
    limit: int = Query(20, ge=1, le=250),
    currency: str = Query("usd"),
):
    return await market_service.get_top_coins(limit=limit, currency=currency)


@router.get("/coin/{coin_id}")
async def get_coin_detail(
    coin_id: str,
    currency: str = Query("usd"),
):
    result = await market_service.get_coin_detail(coin_id=coin_id, currency=currency)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Coin not found")
    return result


@router.get("/coins")
async def get_coins_bulk(
    ids: str = Query(..., description="Comma-separated coin IDs"),
    currency: str = Query("usd"),
):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(status_code=400, detail="At least one coin ID required")
    return await market_service.get_coins_bulk(ids=id_list, currency=currency)


@router.get("/compare")
async def compare_coins(
    coin1: str = Query(..., description="First coin ID"),
    coin2: str = Query(..., description="Second coin ID"),
    currency: str = Query("usd"),
):
    result = await market_service.compare_coins(coin1=coin1, coin2=coin2, currency=currency)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/trending")
async def get_trending():
    return await market_service.get_trending()


@router.get("/global")
async def get_global_data():
    return await market_service.get_global_data()


@router.get("/search")
async def search_coins(query: str = Query(..., min_length=1)):
    return await market_service.search_coins(query=query)


@router.get("/fear-greed")
async def get_fear_greed_index():
    return await sentiment_service.get_fear_greed_index()


@router.get("/fear-greed/history")
async def get_fear_greed_history(limit: int = Query(30, ge=1, le=365)):
    return await sentiment_service.get_fear_greed_history(limit=limit)
