import httpx
from cachetools import TTLCache
from app.config import settings

cache = TTLCache(maxsize=100, ttl=120)


class DeFiService:

    async def get_top_protocols(self, limit: int = 20) -> list[dict]:
        key = f"protocols_{limit}"
        if key in cache:
            return cache[key]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.DEFILLAMA_BASE_URL}/protocols")
            resp.raise_for_status()
            protocols = resp.json()
            protocols.sort(key=lambda x: x.get("tvl") or 0, reverse=True)
            result = [
                {
                    "name": p.get("name"),
                    "slug": p.get("slug"),
                    "category": p.get("category"),
                    "chain": p.get("chain") or ", ".join(p.get("chains", [])),
                    "tvl": p.get("tvl", 0),
                    "change_1d": p.get("change_1d"),
                    "change_7d": p.get("change_7d"),
                    "mcap": p.get("mcap"),
                    "fdv": p.get("fdv"),
                    "url": p.get("url"),
                }
                for p in protocols[:limit]
            ]
            cache[key] = result
            return result

    async def get_protocol_tvl(self, protocol_slug: str) -> dict:
        key = f"tvl_{protocol_slug}"
        if key in cache:
            return cache[key]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.DEFILLAMA_BASE_URL}/tvl/{protocol_slug}")
            resp.raise_for_status()
            result = {"protocol": protocol_slug, "tvl": resp.json()}
            cache[key] = result
            return result

    async def get_yields(self, chain: str | None = None, limit: int = 20) -> list[dict]:
        key = f"yields_{chain}_{limit}"
        if key in cache:
            return cache[key]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.DEFILLAMA_BASE_URL}/pools")
            resp.raise_for_status()
            pools = resp.json().get("data", [])
            if chain:
                pools = [p for p in pools if p.get("chain", "").lower() == chain.lower()]
            pools.sort(key=lambda x: x.get("tvlUsd", 0), reverse=True)
            result = [
                {
                    "pool": p.get("pool"),
                    "project": p.get("project"),
                    "chain": p.get("chain"),
                    "symbol": p.get("symbol"),
                    "tvlUsd": p.get("tvlUsd", 0),
                    "apy": p.get("apy", 0),
                    "apyBase": p.get("apyBase"),
                    "apyReward": p.get("apyReward"),
                    "rewardTokens": p.get("rewardTokens"),
                    "il7d": p.get("il7d"),
                    "apyPct7d": p.get("apyPct7d"),
                }
                for p in pools[:limit]
            ]
            cache[key] = result
            return result

    async def get_stablecoins(self) -> list[dict]:
        if "stablecoins" in cache:
            return cache["stablecoins"]
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{settings.DEFILLAMA_BASE_URL}/stablecoins")
            resp.raise_for_status()
            coins = resp.json().get("peggedAssets", [])
            coins.sort(key=lambda x: x.get("circulating", {}).get("peggedUSD", 0), reverse=True)
            result = [
                {
                    "name": c.get("name"),
                    "symbol": c.get("symbol"),
                    "circulating_usd": c.get("circulating", {}).get("peggedUSD", 0),
                    "chain_circulating": {
                        chain: data.get("current", {}).get("peggedUSD", 0)
                        for chain, data in c.get("chainCirculating", {}).items()
                    },
                }
                for c in coins[:20]
            ]
            cache["stablecoins"] = result
            return result


defi_service = DeFiService()
