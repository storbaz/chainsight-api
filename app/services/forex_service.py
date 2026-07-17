import time
import httpx
from cachetools import TTLCache

cache = TTLCache(maxsize=200, ttl=300)
http_client = httpx.AsyncClient(timeout=15)

FRANKFURTER_BASE = "https://api.frankfurter.dev/v1"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

MAJOR_FOREX = [
    "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF",
    "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/GBP", "EUR/JPY", "GBP/JPY",
    "USD/CNY", "USD/HKD", "USD/SGD",
]

MAJOR_STOCKS = [
    "SPY", "QQQ", "DIA", "IWM",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
]

COMMODITIES = [
    "GC=F", "SI=F", "CL=F", "NG=F",
]

FOREX_TO_YAHOO = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "USD/CNY": "USDCNY=X",
    "USD/HKD": "USDHKD=X",
    "USD/SGD": "USDSGD=X",
}

ALL_PAIRS = MAJOR_FOREX + MAJOR_STOCKS + COMMODITIES


class ForexService:

    async def get_latest_rates(self, base: str = "EUR", symbols: str = "") -> dict:
        key = f"rates_{base}_{symbols}"
        if key in cache:
            return cache[key]

        params = {"from": base}
        if symbols:
            params["to"] = symbols

        try:
            resp = await http_client.get(f"{FRANKFURTER_BASE}/latest", params=params)
            resp.raise_for_status()
            data = resp.json()
            result = {
                "base": data.get("base"),
                "date": data.get("date"),
                "rates": data.get("rates", {}),
                "source": "Frankfurter (ECB)",
            }
            cache[key] = result
            return result
        except Exception as e:
            return {"error": str(e)}

    async def get_pairs_overview(self) -> dict:
        key = "pairs_overview"
        if key in cache:
            return cache[key]

        pairs = []

        # Forex pairs from Frankfurter
        try:
            resp = await http_client.get(
                f"{FRANKFURTER_BASE}/latest",
                params={"from": "EUR", "to": "USD,GBP,JPY,CHF,CAD,AUD,NZD,CNY,HKD,SGD"},
            )
            resp.raise_for_status()
            eur_rates = resp.json().get("rates", {})

            cross_rates = {}
            for curr in ["USD", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]:
                try:
                    resp2 = await http_client.get(
                        f"{FRANKFURTER_BASE}/latest",
                        params={"from": curr, "to": "USD,GBP,JPY,EUR"},
                    )
                    resp2.raise_for_status()
                    cross_rates[curr] = resp2.json().get("rates", {})
                except Exception:
                    pass

            for pair in MAJOR_FOREX:
                base, quote = pair.split("/")
                rate = None
                if base == "EUR" and quote in eur_rates:
                    rate = eur_rates[quote]
                elif base in cross_rates and quote in cross_rates[base]:
                    rate = cross_rates[base][quote]
                elif quote == "EUR" and base in eur_rates:
                    rate = round(1 / eur_rates[base], 6) if eur_rates[base] else None

                if rate:
                    pairs.append({
                        "pair": pair,
                        "rate": round(rate, 6),
                        "type": "forex",
                        "source": "ECB",
                    })
        except Exception:
            pass

        # Stocks and commodities from Yahoo Finance
        yahoo_symbols = MAJOR_STOCKS + COMMODITIES
        for symbol in yahoo_symbols:
            try:
                resp = await http_client.get(
                    f"{YAHOO_BASE}/{symbol}",
                    params={"interval": "1d", "range": "1d"},
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp.raise_for_status()
                data = resp.json()
                meta = data["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice", 0)
                prev = meta.get("chartPreviousClose", price)
                change_pct = round(((price - prev) / prev) * 100, 2) if prev else 0

                pairs.append({
                    "pair": symbol,
                    "rate": round(price, 2),
                    "change_24h": change_pct,
                    "previous_close": round(prev, 2),
                    "type": "stock" if symbol in MAJOR_STOCKS else "commodity",
                    "name": meta.get("shortName", symbol),
                    "source": "Yahoo Finance",
                })
            except Exception:
                pass

        result = {
            "pairs": pairs,
            "total": len(pairs),
            "timestamp": int(time.time()),
        }
        cache[key] = result
        return result

    async def get_pair_history(
        self, symbol: str, range_: str = "1mo", interval: str = "1d"
    ) -> dict:
        yahoo_symbol = FOREX_TO_YAHOO.get(symbol.upper(), symbol.upper())
        key = f"hist_{yahoo_symbol}_{range_}_{interval}"
        if key in cache:
            return cache[key]

        try:
            resp = await http_client.get(
                f"{YAHOO_BASE}/{yahoo_symbol}",
                params={"interval": interval, "range": range_},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            result_data = data["chart"]["result"][0]
            meta = result_data["meta"]
            timestamps = result_data.get("timestamp", [])
            quotes = result_data.get("indicators", {}).get("quote", [{}])[0]

            closes = quotes.get("close", [])
            opens = quotes.get("open", [])
            highs = quotes.get("high", [])
            lows = quotes.get("low", [])

            candles = []
            for i in range(len(timestamps)):
                if closes[i] is not None:
                    candles.append({
                        "timestamp": timestamps[i],
                        "open": round(opens[i], 6) if opens[i] else None,
                        "high": round(highs[i], 6) if highs[i] else None,
                        "low": round(lows[i], 6) if lows[i] else None,
                        "close": round(closes[i], 6),
                    })

            price_vals = [c["close"] for c in candles]
            result = {
                "symbol": symbol.upper(),
                "yahoo_symbol": yahoo_symbol,
                "name": meta.get("shortName", symbol),
                "type": "forex" if "X" in yahoo_symbol else "stock",
                "range": range_,
                "interval": interval,
                "candles": candles,
                "candles_count": len(candles),
                "summary": {
                    "current": round(meta.get("regularMarketPrice", 0), 6),
                    "previous_close": round(meta.get("chartPreviousClose", 0), 6),
                    "52w_high": round(meta.get("fiftyTwoWeekHigh", 0), 6),
                    "52w_low": round(meta.get("fiftyTwoWeekLow", 0), 6),
                } if meta else {},
                "source": "Yahoo Finance",
            }
            cache[key] = result
            return result

        except Exception as e:
            return {"error": str(e), "symbol": symbol}

    async def get_market_overview(self) -> dict:
        key = "market_overview"
        if key in cache:
            return cache[key]

        overview = {"forex": [], "stocks": [], "commodities": []}

        try:
            overview_data = await self.get_pairs_overview()
            for pair in overview_data.get("pairs", []):
                ptype = pair.get("type", "")
                item = {
                    "symbol": pair.get("pair"),
                    "price": pair.get("rate"),
                    "change_24h": pair.get("change_24h"),
                    "name": pair.get("name", pair.get("pair")),
                }
                if ptype == "forex":
                    overview["forex"].append(item)
                elif ptype == "stock":
                    overview["stocks"].append(item)
                elif ptype == "commodity":
                    overview["commodities"].append(item)
        except Exception:
            pass

        result = {
            "forex": overview["forex"][:10],
            "stocks": overview["stocks"][:12],
            "commodities": overview["commodities"][:5],
            "timestamp": int(time.time()),
        }
        cache[key] = result
        return result

    async def search_pairs(self, query: str) -> list[dict]:
        query = query.upper().strip()
        results = []
        for pair in ALL_PAIRS:
            if query in pair.replace("/", "") or query in pair:
                results.append({"symbol": pair, "type": "forex" if "/" in pair else "stock"})
        return results[:10]


forex_service = ForexService()
