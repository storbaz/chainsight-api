import httpx
from cachetools import TTLCache
from app.services.chains import CHAINS

cache = TTLCache(maxsize=200, ttl=300)
http_client = httpx.AsyncClient(timeout=15)

GOPLUS_BASE = "https://api.gopluslabs.io/api/v1"

CHAIN_ID_MAP = {
    "ethereum": 1,
    "bsc": 56,
    "polygon": 137,
    "arbitrum": 42161,
    "base": 8453,
    "optimism": 10,
    "avalanche": 43114,
}


class SecurityService:

    async def check_honeypot(
        self, address: str, chain: str = "ethereum"
    ) -> dict:
        chain_id = CHAIN_ID_MAP.get(chain)
        if not chain_id:
            return {"error": f"Chain '{chain}' not supported for honeypot check"}

        key = f"hp_{chain}_{address.lower()}"
        if key in cache:
            return cache[key]

        try:
            resp = await http_client.get(
                f"{GOPLUS_BASE}/token_security/{chain_id}",
                params={"contract_addresses": address},
            )
            resp.raise_for_status()
            data = resp.json()
            result_data = data.get("result", {}).get(address.lower(), {})

            if not result_data:
                return {"error": "Token not found on this chain", "chain": chain, "address": address}

            buy_tax = float(result_data.get("buy_tax", 0) or 0)
            sell_tax = float(result_data.get("sell_tax", 0) or 0)
            is_open_source = result_data.get("is_open_source") == "1"
            owner_change_balance = result_data.get("owner_change_balance") == "1"
            hidden_owner = result_data.get("hidden_owner") == "1"
            selfdestruct = result_data.get("is_selfdestruct") == "1"
            external_call = result_data.get("external_call") == "1"
            can_take_back_ownership = result_data.get("can_take_back_ownership") == "1"
            is_proxy = result_data.get("is_proxy") == "1"
            slippage_modifiable = result_data.get("slippage_modifiable") == "1"
            trading_cooldown = result_data.get("trading_cooldown") == "1"
            cannot_sell_all = result_data.get("cannot_sell_all") == "1"
            is_honeypot = result_data.get("is_honeypot") == "1"

            risk_flags = []
            risk_score = 0

            if is_honeypot:
                risk_flags.append("HONEYPOT DETECTED - You CANNOT sell this token")
                risk_score += 50
            if cannot_sell_all:
                risk_flags.append("Cannot sell full balance")
                risk_score += 30
            if buy_tax > 0.1:
                risk_flags.append(f"High buy tax: {buy_tax*100:.1f}%")
                risk_score += 20
            if sell_tax > 0.1:
                risk_flags.append(f"High sell tax: {sell_tax*100:.1f}%")
                risk_score += 25
            if slippage_modifiable:
                risk_flags.append("Slippage can be modified by owner (trap)")
                risk_score += 15
            if owner_change_balance:
                risk_flags.append("Owner can change balances")
                risk_score += 25
            if hidden_owner:
                risk_flags.append("Hidden owner detected")
                risk_score += 10
            if can_take_back_ownership:
                risk_flags.append("Ownership can be reclaimed after renouncement")
                risk_score += 10
            if selfdestruct:
                risk_flags.append("Contract can self-destruct")
                risk_score += 15
            if external_call:
                risk_flags.append("External calls detected (possible exploit vector)")
                risk_score += 5
            if not is_open_source:
                risk_flags.append("Contract source not verified")
                risk_score += 10
            if trading_cooldown:
                risk_flags.append("Trading cooldown active")
                risk_score += 5
            if is_proxy:
                risk_flags.append("Proxy contract (logic can change)")
                risk_score += 5

            risk_score = min(risk_score, 100)

            if risk_score >= 70:
                verdict = "DANGER - High probability of scam"
            elif risk_score >= 40:
                verdict = "SUSPICIOUS - Proceed with caution"
            elif risk_score >= 15:
                verdict = "LOW RISK - Some warnings found"
            else:
                verdict = "SAFE - No major red flags detected"

            result = {
                "chain": chain,
                "address": address,
                "is_honeypot": is_honeypot,
                "risk_score": risk_score,
                "verdict": verdict,
                "risk_flags": risk_flags,
                "token_data": {
                    "buy_tax": round(buy_tax * 100, 2),
                    "sell_tax": round(sell_tax * 100, 2),
                    "is_open_source": is_open_source,
                    "owner_change_balance": owner_change_balance,
                    "hidden_owner": hidden_owner,
                    "slippage_modifiable": slippage_modifiable,
                    "trading_cooldown": trading_cooldown,
                    "cannot_sell_all": cannot_sell_all,
                    "is_proxy": is_proxy,
                    "self_destruct": selfdestruct,
                    "external_call": external_call,
                    "holder_count": int(result_data.get("holder_count", 0) or 0),
                    "lp_holder_count": int(result_data.get("lp_holder_count", 0) or 0),
                    "lp_total_supply": float(result_data.get("lp_total_supply", 0) or 0),
                    "is_true_token": result_data.get("is_true_token") == "1",
                },
                "source": "GoPlus Security",
            }

            cache[key] = result
            return result

        except Exception as e:
            return {"error": f"Failed to check honeypot: {str(e)}", "chain": chain, "address": address}

    async def get_token_security(
        self, address: str, chain: str = "ethereum"
    ) -> dict:
        chain_id = CHAIN_ID_MAP.get(chain)
        if not chain_id:
            return {"error": f"Chain '{chain}' not supported"}

        key = f"sec_{chain}_{address.lower()}"
        if key in cache:
            return cache[key]

        try:
            resp = await http_client.get(
                f"{GOPLUS_BASE}/token_security/{chain_id}",
                params={"contract_addresses": address},
            )
            resp.raise_for_status()
            data = resp.json()
            result_data = data.get("result", {}).get(address.lower(), {})

            if not result_data:
                return {"error": "Token not found", "chain": chain, "address": address}

            result = {
                "chain": chain,
                "address": address,
                "token_name": result_data.get("token_name", ""),
                "token_symbol": result_data.get("token_symbol", ""),
                "total_supply": result_data.get("total_supply", ""),
                "holder_count": int(result_data.get("holder_count", 0) or 0),
                "creator_balance": float(result_data.get("creator_balance", 0) or 0),
                "creator_percent": float(result_data.get("creator_percent", 0) or 0),
                "top_10_holder_rate": float(result_data.get("top_10_holder_rate", 0) or 0),
                "is_open_source": result_data.get("is_open_source") == "1",
                "is_proxy": result_data.get("is_proxy") == "1",
                "is_mintable": result_data.get("is_mintable") == "1",
                "owner_change_balance": result_data.get("owner_change_balance") == "1",
                "can_take_back_ownership": result_data.get("can_take_back_ownership") == "1",
                "hidden_owner": result_data.get("hidden_owner") == "1",
                "selfdestruct": result_data.get("is_selfdestruct") == "1",
                "external_call": result_data.get("external_call") == "1",
                "buy_tax": round(float(result_data.get("buy_tax", 0) or 0) * 100, 2),
                "sell_tax": round(float(result_data.get("sell_tax", 0) or 0) * 100, 2),
                "is_honeypot": result_data.get("is_honeypot") == "1",
                "slippage_modifiable": result_data.get("slippage_modifiable") == "1",
                "trading_cooldown": result_data.get("trading_cooldown") == "1",
                "cannot_sell_all": result_data.get("cannot_sell_all") == "1",
                "dex_list": [
                    {
                        "name": dex.get("name", ""),
                        "liquidity": float(dex.get("liquidity", 0) or 0),
                    }
                    for dex in result_data.get("dex", []) if isinstance(dex, dict)
                ],
                "source": "GoPlus Security",
            }

            cache[key] = result
            return result

        except Exception as e:
            return {"error": str(e), "chain": chain, "address": address}

    async def batch_security_check(
        self, addresses: list[dict]
    ) -> list[dict]:
        results = []
        for item in addresses[:10]:
            addr = item.get("address", "")
            chain = item.get("chain", "ethereum")
            if not addr:
                continue
            result = await self.check_honeypot(addr, chain)
            results.append(result)
        return results


security_service = SecurityService()
