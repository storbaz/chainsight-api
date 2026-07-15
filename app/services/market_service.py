import asyncio
import httpx
from cachetools import TTLCache
from app.config import settings

cache = TTLCache(maxsize=100, ttl=300)
stale_cache: dict = {}
http_client = httpx.AsyncClient(timeout=10)


class MarketService:

    async def _fetch_with_retry(self, url: str, params: dict, retries: int = 2) -> dict:
        for attempt in range(retries):
            try:
                resp = await http_client.get(url, params=params)
                if resp.status_code == 429:
                    if attempt < retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    raise Exception("Rate limited")
                resp.raise_for_status()
                return resp.json()
            except Exception:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 * (attempt + 1))

    async def _fetch_paprika_top(self, limit: int = 10) -> list[dict]:
        try:
            resp = await http_client.get(
                "https://api.coinpaprika.com/v1/tickers",
                params={"limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "id": c.get("id", "").replace("-", "-"),
                    "symbol": c.get("symbol", ""),
                    "name": c.get("name", ""),
                    "current_price": c.get("quotes", {}).get("USD", {}).get("price", 0),
                    "market_cap": c.get("quotes", {}).get("USD", {}).get("market_cap", 0),
                    "market_cap_rank": c.get("rank", 0),
                    "total_volume": c.get("quotes", {}).get("USD", {}).get("volume_24h", 0),
                    "price_change_percentage_24h": c.get("quotes", {}).get("USD", {}).get("percent_change_24h", 0),
                    "price_change_percentage_7d": c.get("quotes", {}).get("USD", {}).get("percent_change_7d", 0),
                }
                for c in data
            ]
        except Exception:
            return []

    async def get_top_coins(self, limit: int = 20, currency: str = "usd") -> list[dict]:
        key = f"top_{limit}_{currency}"
        if key in cache:
            return cache[key]
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/coins/markets",
                params={
                    "vs_currency": currency,
                    "order": "market_cap_desc",
                    "per_page": limit,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "7d",
                },
            )
            cache[key] = data
            stale_cache[key] = data
            return data
        except Exception:
            if key in stale_cache:
                return stale_cache[key]
            fallback = await self._fetch_paprika_top(limit)
            if fallback:
                cache[key] = fallback
                stale_cache[key] = fallback
                return fallback
            return []

    async def get_coin_detail(self, coin_id: str, currency: str = "usd") -> dict:
        key = f"coin_{coin_id}_{currency}"
        if key in cache:
            return cache[key]
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/coins/{coin_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                    "sparkline": "false",
                },
            )
            md = data.get("market_data", {})
            result = {
                "id": data.get("id"),
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "description": data.get("description", {}).get("en", "")[:500],
                "current_price": md.get("current_price", {}).get(currency, 0),
                "market_cap": md.get("market_cap", {}).get(currency, 0),
                "market_cap_rank": md.get("market_cap_rank"),
                "total_volume": md.get("total_volume", {}).get(currency, 0),
                "high_24h": md.get("high_24h", {}).get(currency, 0),
                "low_24h": md.get("low_24h", {}).get(currency, 0),
                "price_change_percentage_24h": md.get("price_change_percentage_24h", 0),
                "price_change_percentage_7d": md.get("price_change_percentage_7d"),
                "price_change_percentage_30d": md.get("price_change_percentage_30d"),
                "circulating_supply": md.get("circulating_supply", 0),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
                "ath": md.get("ath", {}).get(currency, 0),
                "ath_change_percentage": md.get("ath_change_percentage", {}).get(currency, 0),
                "ath_date": md.get("ath_date", {}).get(currency, ""),
                "last_updated": md.get("last_updated", ""),
            }
            cache[key] = result
            stale_cache[key] = result
            return result
        except Exception:
            if key in stale_cache:
                return stale_cache[key]
            return {"error": "not_found"}

    async def get_global_data(self) -> dict:
        key = "global"
        if key in cache:
            return cache[key]
        try:
            d = (await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/global", {}
            )).get("data", {})
            result = {
                "total_market_cap": d.get("total_market_cap", {}),
                "total_volume": d.get("total_volume", {}),
                "market_cap_percentage": d.get("market_cap_percentage", {}),
                "active_cryptocurrencies": d.get("active_cryptocurrencies", 0),
                "markets": d.get("markets", 0),
                "market_cap_change_percentage_24h_usd": d.get("market_cap_change_percentage_24h_usd", 0),
            }
            cache[key] = result
            stale_cache[key] = result
            return result
        except Exception:
            return stale_cache.get(key, {})

    async def search_coins(self, query: str) -> list[dict]:
        key = f"search_{query}"
        if key in cache:
            return cache[key]
        try:
            coins = (await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/search",
                params={"query": query},
            )).get("coins", [])
            result = [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "symbol": c.get("symbol"),
                    "market_cap_rank": c.get("market_cap_rank"),
                }
                for c in coins[:10]
            ]
            cache[key] = result
            stale_cache[key] = result
            return result
        except Exception:
            return stale_cache.get(key, [])


market_service = MarketService()
