import asyncio
import time
import httpx
from cachetools import TTLCache
from app.config import settings
from app.services.chains import CHAINS, WHALE_ADDRESSES

cache = TTLCache(maxsize=200, ttl=600)
stale_cache: dict = {}
http_client = httpx.AsyncClient(timeout=15)


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

        if key in stale_cache:
            asyncio.create_task(self._refresh_whales(chain, chain_conf, min_value, limit, key))
            return stale_cache[key]

        if chain == "bitcoin":
            return await self._get_bitcoin_whales(min_value, limit, key)
        if chain == "solana":
            return await self._get_solana_whales(min_value, limit, key)

        return await self._get_evm_whales(chain, chain_conf, min_value, limit, key)

    async def _refresh_whales(self, chain, chain_conf, min_value, limit, key):
        try:
            if chain == "solana":
                result = await self._get_solana_whales(min_value, limit, key)
            else:
                result = await self._get_evm_whales(chain, chain_conf, min_value, limit, key)
            stale_cache[key] = result
        except Exception:
            pass

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
                stale_cache[key] = results[:limit]
                return results[:limit]
            except Exception as e:
                return stale_cache.get(key, [{"error": str(e)}])

        all_results = []
        chain_id = chain_conf.get("chain_id", 1)

        async def _fetch_addr_txs(addr_info: dict) -> list[dict]:
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
                    return []
                symbol = chain_conf["symbol"]
                results = []
                for tx in data:
                    value_native = int(tx.get("value", "0")) / 1e18
                    if value_native >= min_value:
                        results.append({
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
                return results
            except Exception:
                return []

        addr_results = await asyncio.gather(
            *[_fetch_addr_txs(a) for a in addresses[:3]]
        )
        for r in addr_results:
            all_results.extend(r)

        all_results.sort(key=lambda x: x.get("value", 0), reverse=True)
        if not all_results:
            all_results = [{"message": f"No whale transactions found on {chain_conf['name']}"}]
        cache[key] = all_results[:limit]
        stale_cache[key] = all_results[:limit]
        return all_results[:limit]

    async def _get_bitcoin_whales(self, min_value: float, limit: int, key: str) -> list[dict]:
        try:
            resp = await http_client.get(
                "https://blockstream.info/api/mempool/recent",
                timeout=15,
            )
            resp.raise_for_status()
            txs = resp.json()

            results = []
            for tx in txs:
                total_out = sum(o.get("value", 0) for o in tx.get("vout", []))
                btc_value = total_out / 1e8
                if btc_value >= min_value:
                    results.append({
                        "chain": "bitcoin",
                        "hash": tx.get("txid", ""),
                        "from_address": "multiple inputs",
                        "to_address": tx.get("vout", [{}])[0].get("scriptpubkey_address", "") if tx.get("vout") else "",
                        "value": round(btc_value, 6),
                        "token_symbol": "BTC",
                        "gas_used": tx.get("fee", 0),
                        "gas_price": 0,
                        "block_number": 0,
                        "timestamp": "",
                        "explorer_url": f"https://blockstream.info/tx/{tx.get('txid', '')}",
                    })

            if not results:
                results = [{"message": "No whale BTC transactions in current mempool"}]
            cache[key] = results[:limit]
            stale_cache[key] = results[:limit]
            return results[:limit]
        except Exception as e:
            return stale_cache.get(key, [{"error": str(e)}])

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

        if chain == "bitcoin":
            try:
                resp = await http_client.get("https://blockstream.info/api/fee-estimates", timeout=10)
                resp.raise_for_status()
                fees = resp.json()
                return {
                    "chain": "bitcoin",
                    "chain_name": "Bitcoin",
                    "symbol": "BTC",
                    "low": fees.get("144", 1),
                    "average": fees.get("6", 5),
                    "fast": fees.get("1", 20),
                    "unit": "sat/vB",
                }
            except Exception:
                return {"error": "Failed to get Bitcoin fee estimates"}

        key = f"gas_{chain}"
        if key in cache:
            return cache[key]

        rpc = chain_conf["rpc"]

        base_gwei = 0

        # Try RPC first
        try:
            rpc_resp = await http_client.post(
                rpc,
                json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 1},
                timeout=10,
            )
            rpc_resp.raise_for_status()
            hex_price = rpc_resp.json().get("result", "0x0")
            base_gwei = int(hex_price, 16) / 1e9
        except Exception:
            pass

        # Try Etherscan gas oracle (best source)
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

        # Try Blocknative public API (no key needed, ETH only)
        if chain == "ethereum" and base_gwei == 0:
            try:
                resp = await http_client.get(
                    "https://api.blocknative.com/gasprices/blockprices",
                    headers={"Authorization": settings.ETHERSCAN_API_KEY or "public"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    bp = resp.json().get("blockPrices", [{}])[0].get("estimatedPrices", [{}])
                    if bp:
                        base_gwei = bp[0].get("price", 20)
            except Exception:
                pass

        if base_gwei > 0:
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

        return cache.get(key, {"error": f"Failed to get gas for {chain}. Set ETHERSCAN_API_KEY on Render."})

    async def get_all_chains_gas(self) -> list[dict]:
        results = await asyncio.gather(
            *[self.get_gas_estimate(chain) for chain in CHAINS]
        )
        return results


whale_service = WhaleService()
