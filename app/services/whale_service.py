import httpx
from cachetools import TTLCache
from app.config import settings
from app.services.chains import CHAINS, WHALE_ADDRESSES

cache = TTLCache(maxsize=200, ttl=300)
http_client = httpx.AsyncClient(timeout=30)


class WhaleService:

    async def get_whale_transactions(
        self, chain: str = "ethereum", min_value: float = 100, limit: int = 20
    ) -> list[dict]:
        chain_conf = CHAINS.get(chain)
        if not chain_conf:
            return [{"error": f"Chain '{chain}' not supported. Use: {list(CHAINS.keys())}"}]

        key = f"whales_{chain}_{min_value}_{limit}"
        if key in cache:
            return cache[key]

        if chain == "solana":
            return await self._get_solana_whales(min_value, limit, key)

        return await self._get_evm_whales(chain, chain_conf, min_value, limit, key)

    async def _get_evm_whales(
        self, chain: str, chain_conf: dict, min_value: float, limit: int, key: str
    ) -> list[dict]:
        addresses = WHALE_ADDRESSES.get(chain, [])
        if not addresses:
            chain_id = chain_conf.get("chain_id", 1)
            try:
                resp = await http_client.get(
                    settings.ETHERSCAN_BASE_URL,
                    params={
                        "chainid": chain_id,
                        "module": "account",
                        "action": "txlistinternal",
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

                symbol = chain_conf["symbol"]
                results = []
                for tx in data:
                    value_native = int(tx.get("value", "0")) / 1e18
                    if value_native >= min_value:
                        results.append({
                            "chain": chain,
                            "hash": tx.get("hash"),
                            "from_address": tx.get("from"),
                            "to_address": tx.get("to"),
                            "value": round(value_native, 4),
                            "token_symbol": symbol,
                            "gas_used": int(tx.get("gasUsed", 0)),
                            "gas_price": int(tx.get("gasPrice", 0)) / 1e9,
                            "block_number": int(tx.get("blockNumber", 0)),
                            "timestamp": tx.get("timeStamp", ""),
                            "explorer_url": f"{chain_conf['explorer_url']}/tx/{tx.get('hash', '')}",
                        })
                if not results:
                    results = [{"message": f"No whale transactions on {chain_conf['name']} in recent blocks"}]
                cache[key] = results[:limit]
                return results[:limit]
            except Exception as e:
                return cache.get(key, [{"error": str(e)}])

        all_results = []
        chain_id = chain_conf.get("chain_id", 1)
        for addr_info in addresses[:3]:
            try:
                resp = await http_client.get(
                    settings.ETHERSCAN_BASE_URL,
                    params={
                        "chainid": chain_id,
                        "module": "account",
                        "action": "txlistinternal",
                        "address": addr_info["address"],
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": 1,
                        "offset": 30,
                        "sort": "desc",
                        "apikey": settings.ETHERSCAN_API_KEY,
                    },
                )
                resp.raise_for_status()
                data = resp.json().get("result", [])
                if isinstance(data, str):
                    continue

                symbol = chain_conf["symbol"]
                for tx in data:
                    value_native = int(tx.get("value", "0")) / 1e18
                    if value_native >= min_value:
                        all_results.append({
                            "chain": chain,
                            "label": addr_info.get("label", ""),
                            "hash": tx.get("hash"),
                            "from_address": tx.get("from"),
                            "to_address": tx.get("to"),
                            "value": round(value_native, 4),
                            "token_symbol": symbol,
                            "gas_used": int(tx.get("gasUsed", 0)),
                            "gas_price": int(tx.get("gasPrice", 0)) / 1e9,
                            "block_number": int(tx.get("blockNumber", 0)),
                            "timestamp": tx.get("timeStamp", ""),
                            "explorer_url": f"{chain_conf['explorer_url']}/tx/{tx.get('hash', '')}",
                        })
            except Exception:
                continue

        all_results.sort(key=lambda x: x.get("value", 0), reverse=True)
        if not all_results:
            all_results = [{"message": f"No whale transactions found on {chain_conf['name']}"}]
        cache[key] = all_results[:limit]
        return all_results[:limit]

    async def _get_solana_whales(self, min_value: float, limit: int, key: str) -> list[dict]:
        try:
            resp = await http_client.post(
                "https://api.mainnet-beta.solana.com",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getRecentBlockhash",
                },
            )
            resp.raise_for_status()

            resp2 = await http_client.get(
                "https://public-api.solscan.io/transaction/last",
                params={"limit": 50},
                headers={"Accept": "application/json"},
            )

            results = []
            if resp2.status_code == 200:
                data = resp2.json().get("data", [])
                for tx in data:
                    lamports = tx.get("fee", 0)
                    sol_value = lamports / 1e9
                    if sol_value >= min_value:
                        results.append({
                            "chain": "solana",
                            "hash": tx.get("txHash", ""),
                            "from_address": tx.get("feePayer", ""),
                            "to_address": "",
                            "value": round(sol_value, 4),
                            "token_symbol": "SOL",
                            "gas_used": tx.get("fee", 0),
                            "gas_price": 0,
                            "block_number": tx.get("slot", 0),
                            "timestamp": str(tx.get("blockTime", "")),
                            "explorer_url": f"https://solscan.io/tx/{tx.get('txHash', '')}",
                        })

            if not results:
                resp3 = await http_client.get(
                    "https://api.mainnet-beta.solana.com",
                    timeout=10,
                )
                results = [{"message": "No whale transactions found on Solana (API limited)"}]

            cache[key] = results[:limit]
            return results[:limit]
        except Exception as e:
            return cache.get(key, [{"error": str(e)}])

    async def get_gas_estimate(self, chain: str = "ethereum") -> dict:
        chain_conf = CHAINS.get(chain)
        if not chain_conf:
            return {"error": f"Chain '{chain}' not supported"}

        key = f"gas_{chain}"
        if key in cache:
            return cache[key]

        rpc = chain_conf["rpc"]

        try:
            rpc_resp = await http_client.post(
                rpc,
                json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
                timeout=10,
            )
            rpc_resp.raise_for_status()
            hex_price = rpc_resp.json().get("result", "0x0")
            base_gwei = int(hex_price, 16) / 1e9

            if chain_conf.get("gas_api") == "etherscan" and settings.ETHERSCAN_API_KEY:
                try:
                    resp = await http_client.get(
                        settings.ETHERSCAN_BASE_URL,
                        params={
                            "chainid": chain_conf["chain_id"],
                            "module": "gastracker",
                            "action": "gasoracle",
                            "apikey": settings.ETHERSCAN_API_KEY,
                        },
                        timeout=10,
                    )
                    resp.raise_for_status()
                    result = resp.json().get("result", {})
                    if isinstance(result, dict) and "SafeGasPrice" in result:
                        gas = {
                            "chain": chain,
                            "chain_name": chain_conf["name"],
                            "symbol": chain_conf["symbol"],
                            "low": float(result.get("SafeGasPrice", 0)),
                            "average": float(result.get("ProposeGasPrice", 0)),
                            "fast": float(result.get("FastGasPrice", 0)),
                            "base_fee": float(result.get("suggestBaseFee", 0)),
                            "unit": "gwei",
                        }
                        cache[key] = gas
                        return gas
                except Exception:
                    pass

            gas = {
                "chain": chain,
                "chain_name": chain_conf["name"],
                "symbol": chain_conf["symbol"],
                "low": round(base_gwei * 0.9, 4),
                "average": round(base_gwei, 4),
                "fast": round(base_gwei * 1.2, 4),
                "base_fee": round(base_gwei, 4),
                "unit": "gwei",
            }
            cache[key] = gas
            return gas
        except Exception:
            return cache.get(key, {"error": f"Failed to get gas for {chain}"})

    async def get_all_chains_gas(self) -> list[dict]:
        results = []
        for chain in CHAINS:
            gas = await self.get_gas_estimate(chain)
            results.append(gas)
        return results


whale_service = WhaleService()
