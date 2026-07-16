import httpx
from cachetools import TTLCache
from app.config import settings

cache = TTLCache(maxsize=100, ttl=600)
http_client = httpx.AsyncClient(timeout=30)


class WhaleService:

    async def get_eth_large_transactions(self, min_value_eth: float = 100) -> list[dict]:
        key = f"whales_{min_value_eth}"
        if key in cache:
            return cache[key]
        try:
            resp = await http_client.get(
                settings.ETHERSCAN_BASE_URL,
                params={
                    "module": "account",
                    "action": "txlist",
                    "address": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
                    "startblock": 0,
                    "endblock": 99999999,
                    "page": 1,
                    "offset": 20,
                    "sort": "desc",
                    "apikey": settings.ETHERSCAN_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("result", [])
            if isinstance(data, str):
                return cache.get(key, [])
            results = []
            for tx in data:
                value_eth = int(tx.get("value", "0")) / 1e18
                if value_eth >= min_value_eth:
                    results.append({
                        "hash": tx.get("hash"),
                        "from_address": tx.get("from"),
                        "to_address": tx.get("to"),
                        "value": round(value_eth, 4),
                        "token_symbol": "ETH",
                        "gas_used": int(tx.get("gasUsed", 0)),
                        "gas_price": int(tx.get("gasPrice", 0)) / 1e9,
                        "block_number": int(tx.get("blockNumber", 0)),
                        "timestamp": tx.get("timeStamp", ""),
                    })
            cache[key] = results
            return results
        except Exception:
            return cache.get(key, [])

    async def get_gas_estimate(self) -> dict:
        if "gas" in cache:
            return cache["gas"]
        try:
            resp = await http_client.get(
                settings.ETHERSCAN_BASE_URL,
                params={
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": settings.ETHERSCAN_API_KEY,
                },
            )
            resp.raise_for_status()
            result = resp.json().get("result", {})
            if isinstance(result, str):
                return cache.get("gas", {"low": 0, "average": 0, "fast": 0, "base_fee": 0, "last_block": 0})
            gas = {
                "low": float(result.get("SafeGasPrice", 0)),
                "average": float(result.get("ProposeGasPrice", 0)),
                "fast": float(result.get("FastGasPrice", 0)),
                "base_fee": float(result.get("suggestBaseFee", 0)),
                "last_block": int(result.get("LastBlock", 0)),
            }
            cache["gas"] = gas
            return gas
        except Exception:
            return cache.get("gas", {"low": 0, "average": 0, "fast": 0, "base_fee": 0, "last_block": 0})


whale_service = WhaleService()
