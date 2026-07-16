import asyncio
import math
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

    async def get_coins_bulk(self, ids: list[str], currency: str = "usd") -> list[dict]:
        key = f"bulk_{','.join(sorted(ids))}_{currency}"
        if key in cache:
            return cache[key]
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/coins/markets",
                params={
                    "vs_currency": currency,
                    "ids": ",".join(ids),
                    "order": "market_cap_desc",
                    "per_page": len(ids),
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "7d",
                },
            )
            if data:
                cache[key] = data
                stale_cache[key] = data
                return data
        except Exception:
            pass
        # Fallback: CoinPaprika
        try:
            resp = await http_client.get(
                "https://api.coinpaprika.com/v1/tickers",
                params={"limit": 200},
            )
            resp.raise_for_status()
            paprika = resp.json()
            id_set = {i.lower() for i in ids}
            data = [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "symbol": c.get("symbol"),
                    "current_price": c.get("quotes", {}).get("USD", {}).get("price", 0),
                    "market_cap": c.get("quotes", {}).get("USD", {}).get("market_cap", 0),
                    "market_cap_rank": c.get("rank"),
                    "total_volume": c.get("quotes", {}).get("USD", {}).get("volume_24h", 0),
                    "price_change_percentage_24h": c.get("quotes", {}).get("USD", {}).get("percent_change_24h", 0),
                    "price_change_percentage_7d": c.get("quotes", {}).get("USD", {}).get("percent_change_7d", 0),
                }
                for c in paprika
                if c.get("id", "").lower() in id_set or c.get("symbol", "").lower() in id_set
            ]
            if data:
                cache[key] = data
                stale_cache[key] = data
                return data
        except Exception:
            pass
        return stale_cache.get(key, [])

    async def compare_coins(self, coin1: str, coin2: str, currency: str = "usd") -> dict:
        key = f"compare_{coin1}_{coin2}_{currency}"
        if key in cache:
            return cache[key]
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/coins/markets",
                params={
                    "vs_currency": currency,
                    "ids": f"{coin1},{coin2}",
                    "sparkline": "false",
                    "price_change_percentage": "7d",
                },
            )
        except Exception:
            data = []
        # Fallback: CoinPaprika
        if len(data) < 2:
            try:
                resp = await http_client.get(
                    "https://api.coinpaprika.com/v1/tickers",
                    params={"limit": 200},
                )
                resp.raise_for_status()
                paprika = resp.json()
                data = [
                    c for c in paprika
                    if c.get("id", "").lower() in [coin1.lower(), coin2.lower()]
                    or c.get("symbol", "").lower() in [coin1.lower(), coin2.lower()]
                ][:2]
                if len(data) < 2:
                    return {"error": "One or both coins not found. Use IDs like 'bitcoin', 'ethereum'"}
                data = [
                    {
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "symbol": c.get("symbol"),
                        "current_price": c.get("quotes", {}).get("USD", {}).get("price", 0),
                        "market_cap": c.get("quotes", {}).get("USD", {}).get("market_cap", 0),
                        "market_cap_rank": c.get("rank"),
                        "total_volume": c.get("quotes", {}).get("USD", {}).get("volume_24h", 0),
                        "price_change_percentage_24h": c.get("quotes", {}).get("USD", {}).get("percent_change_24h", 0),
                        "price_change_percentage_7d": c.get("quotes", {}).get("USD", {}).get("percent_change_7d", 0),
                    }
                    for c in data
                ]
            except Exception:
                return {"error": "Failed to compare coins. Try again later."}
        c1, c2 = data[0], data[1]
        result = {
            "coin1": {
                "id": c1.get("id"),
                "name": c1.get("name"),
                "symbol": c1.get("symbol"),
                "current_price": c1.get("current_price", 0),
                "market_cap": c1.get("market_cap", 0),
                "market_cap_rank": c1.get("market_cap_rank"),
                "total_volume": c1.get("total_volume", 0),
                "price_change_24h": c1.get("price_change_percentage_24h", 0),
                "price_change_7d": c1.get("price_change_percentage_7d", 0),
            },
            "coin2": {
                "id": c2.get("id"),
                "name": c2.get("name"),
                "symbol": c2.get("symbol"),
                "current_price": c2.get("current_price", 0),
                "market_cap": c2.get("market_cap", 0),
                "market_cap_rank": c2.get("market_cap_rank"),
                "total_volume": c2.get("total_volume", 0),
                "price_change_24h": c2.get("price_change_percentage_24h", 0),
                "price_change_7d": c2.get("price_change_percentage_7d", 0),
            },
            "comparison": {
                "price_ratio": round(
                    (c1.get("current_price", 0) or 0) / (c2.get("current_price", 1) or 1), 4
                ),
                "market_cap_diff": (c1.get("market_cap", 0) or 0) - (c2.get("market_cap", 0) or 0),
                "volume_ratio": round(
                    (c1.get("total_volume", 0) or 0) / (c2.get("total_volume", 1) or 1), 4
                ),
            },
        }
        cache[key] = result
        stale_cache[key] = result
        return result

    async def get_trending(self) -> dict:
        key = "trending"
        if key in cache:
            return cache[key]
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/search/trending", {}
            )
            coins = data.get("coins", [])
            result = {
                "trending": [
                    {
                        "id": c.get("item", {}).get("id"),
                        "name": c.get("item", {}).get("name"),
                        "symbol": c.get("item", {}).get("symbol"),
                        "market_cap_rank": c.get("item", {}).get("market_cap_rank"),
                        "price_btc": c.get("item", {}).get("price_btc"),
                        "score": c.get("item", {}).get("score"),
                    }
                    for c in coins
                ]
            }
            cache[key] = result
            stale_cache[key] = result
            return result
        except Exception:
            return stale_cache.get(key, {"trending": []})

    async def get_price_history(
        self, coin_id: str, days: int = 30, currency: str = "usd"
    ) -> dict:
        key = f"history_{coin_id}_{days}_{currency}"
        if key in cache:
            return cache[key]

        cg_days = days if days <= 365 else "max"
        try:
            data = await self._fetch_with_retry(
                f"{settings.COINGECKO_BASE_URL}/coins/{coin_id}/market_chart",
                params={"vs_currency": currency, "days": cg_days, "interval": "daily"},
            )
            prices = data.get("prices", [])
            market_caps = data.get("market_caps", [])
            volumes = data.get("total_volumes", [])

            result = {
                "coin_id": coin_id,
                "currency": currency,
                "days": days,
                "prices": [
                    {"timestamp": int(p[0] / 1000), "price": p[1]}
                    for p in prices
                ],
                "market_caps": [
                    {"timestamp": int(p[0] / 1000), "market_cap": p[1]}
                    for p in market_caps
                ],
                "volumes": [
                    {"timestamp": int(p[0] / 1000), "volume": p[1]}
                    for p in volumes
                ],
                "summary": {},
            }

            if prices:
                price_vals = [p[1] for p in prices]
                result["summary"] = {
                    "start_price": round(price_vals[0], 2),
                    "end_price": round(price_vals[-1], 2),
                    "high": round(max(price_vals), 2),
                    "low": round(min(price_vals), 2),
                    "change_pct": round(
                        ((price_vals[-1] - price_vals[0]) / price_vals[0]) * 100, 2
                    ) if price_vals[0] else 0,
                }

            cache[key] = result
            stale_cache[key] = result
            return result
        except Exception:
            return stale_cache.get(key, {"error": "Failed to fetch price history"})

    async def get_correlation(
        self, coin_ids: list[str], days: int = 30, vs_currency: str = "usd"
    ) -> dict:
        key = f"corr_{','.join(sorted(coin_ids))}_{days}"
        if key in cache:
            return cache[key]

        all_series: dict[str, list[float]] = {}

        for cid in coin_ids:
            if cid.lower() in ("s&p500", "sp500", "spy", "^gspc"):
                prices = await self._fetch_sp500_prices(days)
            else:
                try:
                    data = await self._fetch_with_retry(
                        f"{settings.COINGECKO_BASE_URL}/coins/{cid}/market_chart",
                        params={"vs_currency": vs_currency, "days": days, "interval": "daily"},
                    )
                    raw = data.get("prices", [])
                    prices = [p[1] for p in raw]
                except Exception:
                    prices = []

            all_series[cid] = prices

        min_len = min((len(v) for v in all_series.values()), default=0)
        if min_len < 3:
            return {"error": "Not enough data points to compute correlation", "series_lengths": {k: len(v) for k, v in all_series.items()}}

        returns: dict[str, list[float]] = {}
        for cid, prices in all_series.items():
            trimmed = prices[:min_len]
            r = [(trimmed[i] - trimmed[i - 1]) / trimmed[i - 1] for i in range(1, len(trimmed)) if trimmed[i - 1] != 0]
            returns[cid] = r

        n = min(len(v) for v in returns.values())
        matrix: dict[str, dict[str, float]] = {}
        for a in coin_ids:
            matrix[a] = {}
            for b in coin_ids:
                if a == b:
                    matrix[a][b] = 1.0
                elif b in matrix and a in matrix.get(b, {}):
                    matrix[a][b] = matrix[b][a]
                else:
                    matrix[a][b] = round(self._pearson(returns[a][:n], returns[b][:n]), 4)

        avg_returns = {}
        for cid in coin_ids:
            r = returns[cid][:n]
            avg_returns[cid] = round(sum(r) / len(r) * 100, 4) if r else 0

        result = {
            "days": days,
            "assets": coin_ids,
            "data_points": n,
            "correlation_matrix": matrix,
            "avg_daily_return_pct": avg_returns,
        }
        cache[key] = result
        stale_cache[key] = result
        return result

    async def _fetch_sp500_prices(self, days: int) -> list[float]:
        try:
            period2 = int(asyncio.get_event_loop().time())
            period1 = period2 - (days * 86400)
            resp = await http_client.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC",
                params={"period1": period1, "period2": period2, "interval": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        except Exception:
            return []

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
        dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
        if dx == 0 or dy == 0:
            return 0.0
        return num / (dx * dy)


market_service = MarketService()
