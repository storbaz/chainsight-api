import math
import time
import httpx
from cachetools import TTLCache
from app.config import settings
from app.services.market_service import market_service

cache = TTLCache(maxsize=100, ttl=300)
http_client = httpx.AsyncClient(timeout=15)


class AlphaService:

    async def get_whale_accumulation(self, min_change_pct: float = 20.0) -> dict:
        key = f"whale_acc_{min_change_pct}"
        if key in cache:
            return cache[key]

        try:
            top_data = await market_service.get_top_coins(limit=100)
            if not top_data:
                top_data = []

            signals = []
            for coin in top_data:
                volume = coin.get("total_volume", 0) or 0
                mcap = coin.get("market_cap", 1) or 1
                vol_mcap_ratio = volume / mcap if mcap > 0 else 0
                price_change = coin.get("price_change_percentage_24h", 0) or 0
                price_change_7d = coin.get("price_change_percentage_7d_in_currency", 0) or 0

                if vol_mcap_ratio > 0.15 and price_change > 0:
                    signal_strength = round(vol_mcap_ratio * 100 + abs(price_change), 1)
                    signals.append({
                        "coin_id": coin.get("id"),
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name"),
                        "price": coin.get("current_price", 0),
                        "price_change_24h": round(price_change, 2),
                        "price_change_7d": round(price_change_7d, 2),
                        "volume_mcap_ratio": round(vol_mcap_ratio, 4),
                        "volume_24h": volume,
                        "market_cap": mcap,
                        "signal": "ACCUMULATION",
                        "strength": min(signal_strength, 100),
                        "reason": f"Volume/MCap ratio {vol_mcap_ratio:.1%} with +{price_change:.1f}% price action",
                    })

            signals.sort(key=lambda x: x["strength"], reverse=True)
            result = {
                "signals": signals[:20],
                "criteria": {
                    "min_volume_mcap_ratio": 0.15,
                    "min_price_change": 0,
                },
                "description": "High volume relative to market cap with positive price action suggests whale accumulation",
                "timestamp": int(time.time()),
            }
            cache[key] = result
            return result

        except Exception as e:
            return {"error": str(e), "signals": []}

    async def get_volume_anomalies(self, min_volume_ratio: float = 3.0) -> dict:
        key = f"vol_anomaly_{min_volume_ratio}"
        if key in cache:
            return cache[key]

        try:
            all_coins = []
            for page in [1, 2, 3]:
                coins = await market_service.get_coins_bulk(
                    ids=[], currency="usd"
                )
                if coins:
                    all_coins.extend(coins)
                if len(coins) < 200:
                    break

            if not all_coins:
                try:
                    resp = await http_client.get(
                        "https://api.coinpaprika.com/v1/tickers",
                        params={"limit": 200},
                    )
                    resp.raise_for_status()
                    paprika = resp.json()
                    all_coins = [
                        {
                            "id": c.get("id"),
                            "symbol": c.get("symbol"),
                            "name": c.get("name"),
                            "current_price": c.get("quotes", {}).get("USD", {}).get("price", 0),
                            "total_volume": c.get("quotes", {}).get("USD", {}).get("volume_24h", 0),
                            "market_cap": c.get("quotes", {}).get("USD", {}).get("market_cap", 0),
                            "price_change_percentage_24h": c.get("quotes", {}).get("USD", {}).get("percent_change_24h", 0),
                        }
                        for c in paprika
                    ]
                except Exception:
                    pass

            anomalies = []
            for coin in all_coins:
                vol = coin.get("total_volume", 0) or 0
                mcap = coin.get("market_cap", 1) or 1
                price = coin.get("current_price", 0) or 0
                change_24h = coin.get("price_change_percentage_24h", 0) or 0

                if price <= 0 or mcap <= 0:
                    continue

                vol_mcap = vol / mcap

                if vol_mcap > min_volume_ratio / 100:
                    anomalies.append({
                        "coin_id": coin.get("id"),
                        "symbol": coin.get("symbol", "").upper(),
                        "name": coin.get("name"),
                        "price": price,
                        "price_change_24h": round(change_24h, 2),
                        "volume_24h": vol,
                        "market_cap": mcap,
                        "volume_mcap_ratio": round(vol_mcap, 4),
                        "anomaly_type": "HIGH_VOLUME" if change_24h >= 0 else "SELL_PRESSURE",
                        "description": f"Volume is {vol_mcap:.1%} of market cap",
                    })

            anomalies.sort(key=lambda x: x["volume_mcap_ratio"], reverse=True)
            result = {
                "anomalies": anomalies[:30],
                "total_scanned": len(all_coins),
                "criteria": {"min_volume_mcap_ratio": min_volume_ratio / 100},
                "timestamp": int(time.time()),
            }
            cache[key] = result
            return result

        except Exception as e:
            return {"error": str(e), "anomalies": []}

    async def get_momentum_signals(self, coin_id: str = "bitcoin", days: int = 30) -> dict:
        key = f"momentum_{coin_id}_{days}"
        if key in cache:
            return cache[key]

        try:
            history = await market_service.get_price_history(coin_id, days=days)
            prices_raw = history.get("prices", [])

            if len(prices_raw) < 14:
                return {"error": "Not enough price data for momentum analysis", "coin_id": coin_id}

            closes = [p.get("price", 0) for p in prices_raw if p.get("price", 0) > 0]
            if len(closes) < 14:
                return {"error": "Insufficient price points", "coin_id": coin_id}

            rsi = self._calculate_rsi(closes, 14)
            ema_12 = self._calculate_ema(closes, 12)
            ema_26 = self._calculate_ema(closes, 26)

            macd_line = [ema_12[i] - ema_26[i] for i in range(len(ema_26))]
            signal_line = self._calculate_ema(macd_line, 9) if len(macd_line) >= 9 else macd_line

            current_rsi = round(rsi[-1], 2) if rsi else 50
            current_macd = round(macd_line[-1], 2) if macd_line else 0
            current_signal = round(signal_line[-1], 2) if signal_line else 0
            macd_histogram = round(current_macd - current_signal, 2)

            current_price = closes[-1]
            sma_20 = round(sum(closes[-20:]) / min(20, len(closes[-20:])), 2)
            sma_50 = round(sum(closes[-50:]) / min(50, len(closes[-50:])), 2)

            bb = self._calculate_bollinger(closes)
            bb_upper = bb["upper"][-1] if bb["upper"] else 0
            bb_lower = bb["lower"][-1] if bb["lower"] else 0
            bb_middle = bb["middle"][-1] if bb["middle"] else 0

            stoch = self._calculate_stochastic(closes)
            stoch_k = stoch["k"][-1] if stoch["k"] else 50
            stoch_d = stoch["d"][-1] if stoch["d"] else 50

            vwap_vals = self._calculate_vwap(closes)
            current_vwap = vwap_vals[-1] if vwap_vals else current_price

            signals = []
            overall_score = 0

            if current_rsi < 30:
                signals.append({"type": "RSI_OVERSOLD", "value": current_rsi, "interpretation": "Potentially oversold - buy opportunity", "weight": 2})
                overall_score += 2
            elif current_rsi > 70:
                signals.append({"type": "RSI_OVERBOUGHT", "value": current_rsi, "interpretation": "Potentially overbought - consider taking profit", "weight": -2})
                overall_score -= 2
            elif current_rsi < 40:
                signals.append({"type": "RSI_LOW", "value": current_rsi, "interpretation": "RSI approaching oversold territory", "weight": 1})
                overall_score += 1
            elif current_rsi > 60:
                signals.append({"type": "RSI_HIGH", "value": current_rsi, "interpretation": "RSI in bullish zone", "weight": 1})
                overall_score += 1

            if macd_histogram > 0 and (len(macd_histogram if isinstance(macd_histogram, list) else [macd_histogram]) > 1 or current_macd > current_signal):
                signals.append({"type": "MACD_BULLISH", "value": current_macd, "interpretation": "MACD above signal line - bullish momentum", "weight": 1})
                overall_score += 1
            elif macd_histogram < 0:
                signals.append({"type": "MACD_BEARISH", "value": current_macd, "interpretation": "MACD below signal line - bearish momentum", "weight": -1})
                overall_score -= 1

            if current_price > sma_20:
                signals.append({"type": "PRICE_ABOVE_SMA20", "value": sma_20, "interpretation": "Price above 20-day SMA - short-term uptrend", "weight": 1})
                overall_score += 1
            else:
                signals.append({"type": "PRICE_BELOW_SMA20", "value": sma_20, "interpretation": "Price below 20-day SMA - short-term downtrend", "weight": -1})
                overall_score -= 1

            if sma_20 > sma_50:
                signals.append({"type": "SMA_CROSS_BULL", "interpretation": "20-day SMA above 50-day SMA - golden cross", "weight": 1})
                overall_score += 1
            else:
                signals.append({"type": "SMA_CROSS_BEAR", "interpretation": "20-day SMA below 50-day SMA - death cross", "weight": -1})
                overall_score -= 1

            if bb_upper > 0:
                if current_price >= bb_upper:
                    signals.append({"type": "BB_UPPER_BREAK", "value": bb_upper, "interpretation": "Price at/above upper Bollinger Band - potential reversal or breakout", "weight": -1})
                    overall_score -= 1
                elif current_price <= bb_lower:
                    signals.append({"type": "BB_LOWER_BREAK", "value": bb_lower, "interpretation": "Price at/below lower Bollinger Band - potential bounce", "weight": 1})
                    overall_score += 1
                else:
                    bb_pct = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
                    if bb_pct > 0.8:
                        signals.append({"type": "BB_NEAR_UPPER", "value": round(bb_pct * 100, 1), "interpretation": f"Price near upper Bollinger Band ({bb_pct:.0%} of range)", "weight": -1})
                        overall_score -= 1
                    elif bb_pct < 0.2:
                        signals.append({"type": "BB_NEAR_LOWER", "value": round(bb_pct * 100, 1), "interpretation": f"Price near lower Bollinger Band ({bb_pct:.0%} of range)", "weight": 1})
                        overall_score += 1

            if stoch_k < 20 and stoch_d < 20:
                signals.append({"type": "STOCH_OVERSOLD", "k": stoch_k, "d": stoch_d, "interpretation": "Stochastic in oversold zone - potential buy", "weight": 2})
                overall_score += 2
            elif stoch_k > 80 and stoch_d > 80:
                signals.append({"type": "STOCH_OVERBOUGHT", "k": stoch_k, "d": stoch_d, "interpretation": "Stochastic in overbought zone - potential sell", "weight": -2})
                overall_score -= 2
            elif stoch_k > stoch_d and stoch_k < 50:
                signals.append({"type": "STOCH_BULL_CROSS", "k": stoch_k, "d": stoch_d, "interpretation": "Stochastic K crossing above D in lower range - bullish", "weight": 1})
                overall_score += 1
            elif stoch_k < stoch_d and stoch_k > 50:
                signals.append({"type": "STOCH_BEAR_CROSS", "k": stoch_k, "d": stoch_d, "interpretation": "Stochastic K crossing below D in upper range - bearish", "weight": -1})
                overall_score -= 1

            if current_vwap > 0:
                if current_price > current_vwap * 1.02:
                    signals.append({"type": "ABOVE_VWAP", "vwap": current_vwap, "interpretation": f"Price above VWAP ({((current_price/current_vwap)-1)*100:.1f}%) - bullish", "weight": 1})
                    overall_score += 1
                elif current_price < current_vwap * 0.98:
                    signals.append({"type": "BELOW_VWAP", "vwap": current_vwap, "interpretation": f"Price below VWAP ({((1-current_price/current_vwap))*100:.1f}%) - bearish", "weight": -1})
                    overall_score -= 1

            if overall_score >= 3:
                bias = "STRONG BUY"
            elif overall_score >= 1:
                bias = "BUY"
            elif overall_score <= -3:
                bias = "STRONG SELL"
            elif overall_score <= -1:
                bias = "SELL"
            else:
                bias = "NEUTRAL"

            result = {
                "coin_id": coin_id,
                "current_price": current_price,
                "period_days": days,
                "indicators": {
                    "rsi_14": current_rsi,
                    "macd": current_macd,
                    "macd_signal": current_signal,
                    "macd_histogram": macd_histogram,
                    "sma_20": sma_20,
                    "sma_50": sma_50,
                    "bollinger_upper": bb_upper,
                    "bollinger_middle": bb_middle,
                    "bollinger_lower": bb_lower,
                    "stochastic_k": stoch_k,
                    "stochastic_d": stoch_d,
                    "vwap": current_vwap,
                },
                "signals": signals,
                "overall_score": overall_score,
                "bias": bias,
                "disclaimer": "This is NOT financial advice. Do your own research.",
                "timestamp": int(time.time()),
                "source": "ChainSight Alpha Engine",
            }

            cache[key] = result
            return result

        except Exception as e:
            return {"error": str(e), "coin_id": coin_id}

    @staticmethod
    def _calculate_rsi(prices: list[float], period: int = 14) -> list[float]:
        if len(prices) < period + 1:
            return [50.0]
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        rsi_values = []
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

        if not rsi_values:
            return [50.0]
        return rsi_values

    @staticmethod
    def _calculate_ema(prices: list[float], period: int) -> list[float]:
        if len(prices) < period:
            return prices[:]
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]
        for p in prices[period:]:
            ema.append(p * multiplier + ema[-1] * (1 - multiplier))
        return ema

    @staticmethod
    def _calculate_bollinger(closes: list[float], period: int = 20, std_dev: float = 2.0) -> dict:
        if len(closes) < period:
            return {"upper": [], "middle": [], "lower": []}
        middle = []
        upper = []
        lower = []
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1: i + 1]
            avg = sum(window) / period
            variance = sum((x - avg) ** 2 for x in window) / period
            std = math.sqrt(variance)
            middle.append(round(avg, 2))
            upper.append(round(avg + std_dev * std, 2))
            lower.append(round(avg - std_dev * std, 2))
        return {"upper": upper, "middle": middle, "lower": lower}

    @staticmethod
    def _calculate_stochastic(closes: list[float], highs: list[float] = None, lows: list[float] = None, period: int = 14) -> dict:
        if len(closes) < period:
            return {"k": [], "d": []}
        if not highs:
            highs = [c * 1.01 for c in closes]
        if not lows:
            lows = [c * 0.99 for c in closes]
        k_values = []
        for i in range(period - 1, len(closes)):
            window_high = max(highs[i - period + 1: i + 1])
            window_low = min(lows[i - period + 1: i + 1])
            if window_high == window_low:
                k_values.append(50.0)
            else:
                k_values.append(round(((closes[i] - window_low) / (window_high - window_low)) * 100, 2))
        d_values = []
        for i in range(len(k_values)):
            start = max(0, i - 2)
            d_values.append(round(sum(k_values[start:i + 1]) / (i - start + 1), 2))
        return {"k": k_values, "d": d_values}

    @staticmethod
    def _calculate_vwap(closes: list[float], volumes: list[float] = None) -> list[float]:
        if not volumes:
            volumes = [1000000] * len(closes)
        cumulative_vol = 0
        cumulative_pv = 0
        vwap_values = []
        for i in range(len(closes)):
            cumulative_vol += volumes[i]
            cumulative_pv += closes[i] * volumes[i]
            vwap_values.append(round(cumulative_pv / cumulative_vol, 2)) if cumulative_vol > 0 else vwap_values.append(closes[i])
        return vwap_values


alpha_service = AlphaService()
