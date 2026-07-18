import asyncio
import time
import logging
import httpx
from cachetools import TTLCache
from app.config import settings
from app.services.chains import CHAINS, WHALE_ADDRESSES

logger = logging.getLogger(__name__)

cache = TTLCache(maxsize=200, ttl=600)
stale_cache: dict = {}
http_client = httpx.AsyncClient(timeout=15)


class WhaleService:

    CHAINS_USING_GOLDRUSH = {"bsc", "arbitrum"}

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

        has_goldrush = chain in self.CHAINS_USING_GOLDRUSH and bool(settings.GOLDRUSH_API_KEY)
        logger.info(f"[Whales] chain={chain} goldrush={has_goldrush} key_set={bool(settings.GOLDRUSH_API_KEY)}")

        if has_goldrush:
            return await self._get_goldrush_whales(chain, chain_conf, min_value, limit, key)

        return await self._get_evm_whales(chain, chain_conf, min_value, limit, key)

    async def _refresh_whales(self, chain, chain_conf, min_value, limit, key):
        try:
            if chain == "solana":
                result = await self._get_solana_whales(min_value, limit, key)
            elif chain in self.CHAINS_USING_GOLDRUSH and settings.GOLDRUSH_API_KEY:
                result = await self._get_goldrush_whales(chain, chain_conf, min_value, limit, key)
            else:
                result = await self._get_evm_whales(chain, chain_conf, min_value, limit, key)
            stale_cache[key] = result
        except Exception:
            pass

    async def _get_evm_whales(
        self, chain: str, chain_conf: dict, min_value: float, limit: int, key: str
    ) -> list[dict]:
        addresses = WHALE_ADDRESSES.get(chain, [])
        all_results = []
        chain_id = chain_conf.get("chain_id", 1)
        symbol = chain_conf["symbol"]

        async def _fetch_addr_txs(addr_info: dict) -> list[dict]:
            try:
                resp = await http_client.get(
                    settings.ETHERSCAN_BASE_URL,
                    params={
                        "chainid": chain_id,
                        "module": "account",
                        "action": "txlist",
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
                data = resp.json()
                result = data.get("result", [])
                if isinstance(result, str):
                    return []
                results = []
                for tx in result:
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

        if addresses:
            addr_results = await asyncio.gather(
                *[_fetch_addr_txs(a) for a in addresses[:3]]
            )
            for r in addr_results:
                all_results.extend(r)

        etherscan_failed = not all_results and "Free API access is not supported" in str(all_results)

        if not all_results:
            all_results = await self._get_rpc_whales(chain, chain_conf, min_value, key)

        all_results.sort(key=lambda x: x.get("value", 0), reverse=True)
        if not all_results:
            all_results = [{"message": f"No whale transactions found on {chain_conf['name']}"}]
        cache[key] = all_results[:limit]
        stale_cache[key] = all_results[:limit]
        return all_results[:limit]

    async def _get_rpc_whales(
        self, chain: str, chain_conf: dict, min_value: float, key: str
    ) -> list[dict]:
        rpc = chain_conf.get("rpc", "")
        if not rpc:
            return []
        whale_addrs = {a["address"].lower() for a in WHALE_ADDRESSES.get(chain, [])}
        if not whale_addrs:
            return []
        symbol = chain_conf["symbol"]
        try:
            resp = await http_client.post(
                rpc,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10,
            )
            resp.raise_for_status()
            latest_hex = resp.json().get("result", "0x0")
            latest = int(latest_hex, 16)
        except Exception:
            return []
        results = []
        blocks_to_scan = 15
        for i in range(blocks_to_scan):
            block_num = latest - i
            block_hex = hex(block_num)
            try:
                resp = await http_client.post(
                    rpc,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getBlockByNumber",
                        "params": [block_hex, True],
                        "id": 1,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                block = resp.json().get("result", {})
                if not block:
                    continue
                ts = int(block.get("timestamp", "0x0"), 16)
                for tx in block.get("transactions", []):
                    if not isinstance(tx, dict):
                        continue
                    tx_from = (tx.get("from") or "").lower()
                    tx_to = (tx.get("to") or "").lower()
                    if tx_from not in whale_addrs and tx_to not in whale_addrs:
                        continue
                    value_hex = tx.get("value", "0x0")
                    value_native = int(value_hex, 16) / 1e18
                    if value_native < min_value:
                        continue
                    label = ""
                    for a in WHALE_ADDRESSES.get(chain, []):
                        if a["address"].lower() in (tx_from, tx_to):
                            label = a.get("label", "")
                            break
                    results.append({
                        "chain": chain,
                        "label": label,
                        "hash": tx.get("hash", ""),
                        "from_address": tx.get("from", ""),
                        "to_address": tx.get("to", ""),
                        "value": round(value_native, 4),
                        "token_symbol": symbol,
                        "gas_used": int(tx.get("gas", "0x0"), 16) if isinstance(tx.get("gas"), str) else 0,
                        "gas_price": int(tx.get("gasPrice", "0x0"), 16) / 1e9 if isinstance(tx.get("gasPrice"), str) else 0,
                        "block_number": block_num,
                        "timestamp": str(ts),
                        "explorer_url": f"{chain_conf['explorer_url']}/tx/{tx.get('hash', '')}",
                    })
            except Exception:
                continue
        return results

    async def _get_goldrush_whales(
        self, chain: str, chain_conf: dict, min_value: float, limit: int, key: str
    ) -> list[dict]:
        addresses = WHALE_ADDRESSES.get(chain, [])
        if not addresses or not settings.GOLDRUSH_API_KEY:
            return []

        goldrush_id = chain_conf.get("goldrush_chain_id", chain)
        all_results = []
        symbol = chain_conf["symbol"]

        async def _fetch_goldrush_addr(addr_info: dict) -> list[dict]:
            try:
                url = f"https://api.covalenthq.com/v1/{goldrush_id}/address/{addr_info['address']}/transfers_v2/"
                logger.info(f"[GoldRush] Fetching {chain} addr={addr_info['address'][:12]}... chain_id={goldrush_id}")
                resp = await http_client.get(
                    url,
                    params={"page-size": 50, "quote-currency": "USD"},
                    headers={"Authorization": f"Bearer {settings.GOLDRUSH_API_KEY}"},
                    timeout=20,
                )
                if resp.status_code != 200:
                    logger.warning(f"[GoldRush] {chain} status={resp.status_code} body={resp.text[:200]}")
                    return []
                data = resp.json()
                items = data.get("data", {}).get("items", [])
                logger.info(f"[GoldRush] {chain} addr={addr_info['address'][:12]}... got {len(items)} items")
                results = []
                for tx in items:
                    transfers = tx.get("transfers", [])
                    for t in transfers:
                        quote = t.get("quote_rate") or 0
                        raw = int(t.get("delta", "0") or "0")
                        decimals = t.get("contract_decimals", 18)
                        value_token = abs(raw) / (10 ** decimals) if decimals else abs(raw)
                        value_usd = abs(float(t.get("quote", 0) or 0))
                        if value_usd < min_value:
                            continue
                        from_addr = t.get("from_address", "")
                        to_addr = t.get("to_address", "")
                        is_outgoing = from_addr.lower() == addr_info["address"].lower()
                        results.append({
                            "chain": chain,
                            "label": addr_info.get("label", ""),
                            "hash": tx.get("tx_hash", ""),
                            "from_address": from_addr,
                            "to_address": to_addr,
                            "value": round(value_usd, 2),
                            "token_symbol": t.get("contract_ticker_symbol", symbol),
                            "token_name": t.get("contract_name", ""),
                            "gas_used": 0,
                            "gas_price": 0,
                            "block_number": tx.get("block_height", 0),
                            "timestamp": tx.get("block_signed_at", ""),
                            "explorer_url": f"{chain_conf['explorer_url']}/tx/{tx.get('tx_hash', '')}",
                            "direction": "outgoing" if is_outgoing else "incoming",
                        })
                return results
            except Exception as e:
                logger.warning(f"[GoldRush] {chain} exception: {e}")
                return []

        addr_results = await asyncio.gather(
            *[_fetch_goldrush_addr(a) for a in addresses[:5]]
        )
        for r in addr_results:
            all_results.extend(r)

        logger.info(f"[GoldRush] {chain} total results: {len(all_results)}")

        if not all_results:
            logger.info(f"[GoldRush] {chain} empty, falling back to RPC")
            all_results = await self._get_rpc_whales(chain, chain_conf, min_value, key)
            if all_results and isinstance(all_results[0], dict) and "message" not in all_results[0]:
                cache[key] = all_results[:limit]
                stale_cache[key] = all_results[:limit]
                return all_results[:limit]

        all_results.sort(key=lambda x: x.get("value", 0), reverse=True)
        if not all_results:
            all_results = [{"message": f"No whale transactions found on {chain_conf['name']}"}]
        cache[key] = all_results[:limit]
        stale_cache[key] = all_results[:limit]
        return all_results[:limit]

    async def _get_bitcoin_whales(self, min_value: float, limit: int, key: str) -> list[dict]:
        try:
            BTC_WHALE_ADDRESSES = [
                "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
                "bc1qgdjqv0av3q56jvd82tkdjpy7gd6pfv9e2m7embe69vu7d2z589qqkthy6",
                "1LQoKistAqcGDMjN3JbujYRe3eXvsYcTe6",
                "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS",
            ]

            all_results = []
            for addr in BTC_WHALE_ADDRESSES[:2]:
                try:
                    resp = await http_client.get(
                        f"https://blockstream.info/api/address/{addr}/txs",
                        timeout=15,
                    )
                    resp.raise_for_status()
                    txs = resp.json()

                    for tx in txs[:10]:
                        total_out = sum(o.get("value", 0) for o in tx.get("vout", []))
                        btc_value = total_out / 1e8
                        if btc_value >= min_value:
                            status = tx.get("status", {})
                            all_results.append({
                                "chain": "bitcoin",
                                "hash": tx.get("txid", ""),
                                "from_address": addr[:12] + "...",
                                "to_address": tx.get("vout", [{}])[0].get("scriptpubkey_address", "")[:12] + "..." if tx.get("vout") else "",
                                "value": round(btc_value, 6),
                                "token_symbol": "BTC",
                                "gas_used": tx.get("fee", 0),
                                "gas_price": 0,
                                "block_number": status.get("block_height", 0),
                                "timestamp": str(status.get("block_time", "")),
                                "explorer_url": f"https://blockstream.info/tx/{tx.get('txid', '')}",
                            })
                except Exception:
                    continue

            if not all_results:
                all_results = [{"message": "No whale BTC transactions found"}]
            all_results.sort(key=lambda x: x.get("value", 0), reverse=True)
            cache[key] = all_results[:limit]
            stale_cache[key] = all_results[:limit]
            return all_results[:limit]
        except Exception as e:
            return stale_cache.get(key, [{"error": str(e)}])

    async def _get_solana_whales(self, min_value: float, limit: int, key: str) -> list[dict]:
        try:
            SOL_WHALE_ADDRESSES = [
                "5tzFkiKscjHKsN2FzXoyFBfiDjQJt3GFZx8p3bHkxQBY",
                "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            ]

            results = []
            for addr in SOL_WHALE_ADDRESSES:
                try:
                    resp = await http_client.post(
                        "https://api.mainnet-beta.solana.com",
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getSignaturesForAddress",
                            "params": [addr, {"limit": 10}],
                        },
                        timeout=15,
                    )
                    resp.raise_for_status()
                    sigs = resp.json().get("result", [])

                    for sig in sigs:
                        slot = sig.get("slot", 0)
                        err = sig.get("err")
                        if err:
                            continue
                        results.append({
                            "chain": "solana",
                            "hash": sig.get("signature", ""),
                            "from_address": addr,
                            "to_address": "",
                            "value": 0,
                            "token_symbol": "SOL",
                            "gas_used": sig.get("fee", 0),
                            "gas_price": 0,
                            "block_number": slot,
                            "timestamp": str(sig.get("blockTime", "")),
                            "explorer_url": f"https://solscan.io/tx/{sig.get('signature', '')}",
                        })
                except Exception:
                    continue

            if not results:
                results = [{"message": "No recent Solana whale transactions found"}]
            cache[key] = results[:limit]
            stale_cache[key] = results[:limit]
            return results[:limit]
        except Exception as e:
            return stale_cache.get(key, [{"error": str(e)}])

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
