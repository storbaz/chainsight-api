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
                    "action": "txlistinternal",
                    "address": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
                    "startblock": 0,
                    "endblock": 99999999,
                    "page": 1,
                    "offset": 50,
                    "sort": "desc",
                    "apikey": settings.ETHERSCAN_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("result", [])
            if isinstance(data, str):
                return cache.get(key, [{"error": data}])
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
            if not results:
                results = [{"message": "No whale transactions found in recent blocks"}]
            cache[key] = results
            return results
        except Exception as e:
            return cache.get(key, [{"error": str(e)}])

    async def get_gas_estimate(self) -> dict:
        if "gas" in cache:
            return cache["gas"]

        # Try Etherscan first
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
            if isinstance(result, dict) and "SafeGasPrice" in result:
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
            pass

        # Fallback: public Ethereum RPC
        try:
            rpc_resp = await http_client.post(
                "https://eth.llamarpc.com",
                json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
            )
            rpc_resp.raise_for_status()
            hex_price = rpc_resp.json().get("result", "0x0")
            base_gwei = int(hex_price, 16) / 1e9
            gas = {
                "low": round(base_gwei * 0.9, 2),
                "average": round(base_gwei, 2),
                "fast": round(base_gwei * 1.2, 2),
                "base_fee": round(base_gwei, 2),
                "last_block": 0,
            }
            cache["gas"] = gas
            return gas
        except Exception:
            return cache.get("gas", {"low": 0, "average": 0, "fast": 0, "base_fee": 0, "last_block": 0})


whale_service = WhaleService()
