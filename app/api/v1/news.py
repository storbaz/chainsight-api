from fastapi import APIRouter, Query
from app.services.news_service import news_service

router = APIRouter(prefix="/market", tags=["Market"])


@router.get("/news")
async def get_crypto_news(
    limit: int = Query(10, ge=1, le=50, description="Max articles"),
    source: str = Query("all", description="Source: all, cointelegraph, cryptonews, bitcoinmagazine, coindesk"),
):
    return await news_service.get_crypto_news(limit=limit, source=source)
