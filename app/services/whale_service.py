import httpx
from app.config import settings


class WhaleService:

    async def get_eth_large_transactions(self, min_value_eth: float = 100) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                settings.ETHERSCAN_BASE_URL,
                params={
                    "module": "account",
                    "action": "txlist",
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
            return results

    async def get_gas_estimate(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                settings.ETHERSCAN_BASE_URL,
                params={
                    "module": "gastracker",
                    "action": "gasoracle",
                    "apikey": settings.ETHERSCAN_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json().get("result", {})
            return {
                "low": float(data.get("SafeGasPrice", 0)),
                "average": float(data.get("ProposeGasPrice", 0)),
                "fast": float(data.get("FastGasPrice", 0)),
                "base_fee": float(data.get("suggestBaseFee", 0)),
                "last_block": int(data.get("LastBlock", 0)),
            }


whale_service = WhaleService()
