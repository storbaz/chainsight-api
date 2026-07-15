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
