"""DEV.to auto-publisher — generates and posts crypto articles."""

import os
import json
import httpx
from datetime import datetime

DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")
DEVTO_API = "https://dev.to/api"
CHAINSIGHT_BASE = "https://chainsight-api.onrender.com"

ARTICLES = [
    {
        "topic": "whales",
        "title": "How to Track Crypto Whale Transactions Across 9 Blockchains with Python",
        "tags": ["python", "crypto", "blockchain", "web3"],
    },
    {
        "topic": "honeypot",
        "title": "How to Detect Honeypot Tokens Before You Buy — A Developer Guide",
        "tags": ["crypto", "security", "solidity", "web3"],
    },
    {
        "topic": "multi_asset",
        "title": "Building a Multi-Asset Dashboard: Crypto, Forex & Stocks in One API",
        "tags": ["python", "api", "finance", "crypto"],
    },
    {
        "topic": "fear_greed",
        "title": "Using Fear & Greed Index Data to Build Smarter Trading Bots",
        "tags": ["python", "crypto", "trading", "api"],
    },
    {
        "topic": "defi",
        "title": "DeFi Yield Farming Data: Find the Best APY Across Protocols with One API",
        "tags": ["defi", "crypto", "ethereum", "api"],
    },
    {
        "topic": "building_in_public",
        "title": "I Built a Free Crypto Intelligence API — Here's What I Learned as a Solo Dev",
        "tags": ["crypto", "building-in-public", "api", "startup"],
    },
    {
        "topic": "bitcoin",
        "title": "Track Bitcoin Whale Movements with Blockstream API and Python",
        "tags": ["bitcoin", "python", "blockchain", "api"],
    },
    {
        "topic": "widgets",
        "title": "How to Embed Real-Time Crypto Data on Any Website with a Free Widget",
        "tags": ["javascript", "crypto", "web-development", "api"],
    },
    {
        "topic": "security",
        "title": "Token Security Audit API: Check Any ERC-20 Contract in Seconds",
        "tags": ["security", "ethereum", "solidity", "api"],
    },
    {
        "topic": "signals",
        "title": "Building Crypto Alpha Signals: RSI, MACD & Volume Anomaly Detection",
        "tags": ["python", "crypto", "trading", "data-science"],
    },
]


def build_article(topic_data: dict, top_coins: list, fear_greed: dict) -> str:
    fv = fear_greed.get("value", 50)
    fc = fear_greed.get("classification", "Neutral")

    coins_md = ""
    for c in top_coins[:5]:
        ch = c.get("price_change_percentage_24h", 0) or 0
        icon = "📈" if ch >= 0 else "📉"
        coins_md += f"- **{c['name']}** (${c['current_price']:,.2f}) {icon} {ch:+.1f}%\n"

    topic = topic_data["topic"]

    if topic == "whales":
        body = f"""## Why Whale Tracking Matters

When a whale moves $50M of ETH, the market notices. Learning to detect these movements before the price reacts gives you an edge.

**Current Market:** Fear & Greed Index at **{fv}/100** ({fc})

{coins_md}

## What the API Provides

The ChainSight API tracks whale transactions across 9 blockchains:

| Chain | Source | Min Trackable |
|-------|--------|--------------|
| Ethereum | Etherscan V2 | 100 ETH |
| Bitcoin | Blockstream Mempool | 1 BTC |
| BSC | Etherscan V2 | 1000 BNB |
| Polygon | Etherscan V2 | 10000 MATIC |
| Arbitrum, Base, OP, Avalanche | Etherscan V2 | Varies |
| Solana | Solscan API | 100 SOL |

## Quick Start

```python
import httpx

API = "https://chainsight-api.onrender.com"

# Get large ETH transactions
resp = httpx.get(f"{{API}}/v1/whales/chain/ethereum", params={{"min_value": 100000}})
for tx in resp.json():
    if "hash" in tx:
        print(f"🐋 {{tx['value']}} ETH — {{tx['from_address'][:12]}}...")
```

## Build a Whale Alert Bot

```python
import httpx, asyncio

API = "https://chainsight-api.onrender.com"

async def monitor():
    last_hash = ""
    while True:
        resp = httpx.get(f"{{API}}/v1/whales/chain/ethereum?min_value=500000")
        txs = resp.json()
        for tx in txs:
            if tx.get("hash") and tx["hash"] != last_hash:
                print(f"🚨 WHALE: {{tx['value']}} ETH moved!")
                last_hash = tx["hash"]
        await asyncio.sleep(60)

asyncio.run(monitor())
```

## What You Can Build

- **Trading bots** that react to whale movements
- **Portfolio alerts** when large wallets move
- **Research dashboards** tracking smart money
- **Risk management** tools detecting exchange outflows

## Try It Free

The API offers a free tier with no credit card:

```bash
curl "https://chainsight-api.onrender.com/v1/whales/chain/ethereum?min_value=100000"
```

🔗 [RapidAPI](https://rapidapi.com/storbaz/api/chainsight) | 🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*ChainSight is open source and free. Built by a solo developer.*"""

    elif topic == "honeypot":
        body = f"""## The $12B Problem

In 2024-2025, over $12 billion was lost to crypto scams. Honeypot tokens — contracts that let you buy but never sell — are among the most common traps.

**Current Market:** Fear & Greed at **{fv}/100** ({fc})

{coins_md}

## What Is a Honeypot?

A honeypot token has hidden sell restrictions:
- Sell taxes of 99%+
- Blacklist functions
- Owner-only trading
- Upgradeable proxy contracts

## Detecting Honeypots with Code

```python
import httpx

API = "https://chainsight-api.onrender.com"

async def check_token(address: str):
    resp = httpx.get(f"{{API}}/v1/security/honeypot/{{address}}")
    data = resp.json()

    if data.get("is_honeypot"):
        print("🚨 HONEYPOT DETECTED — Do not buy!")
        return False

    risk = data.get("risk_level", "unknown")
    sell_tax = data.get("sell_tax", 0)

    if risk == "high" or sell_tax > 10:
        print(f"⚠️ High risk — Sell tax: {{sell_tax}}%")
        return False

    print(f"✅ Looks safe — Risk: {{risk}}")
    return True
```

## Batch Check Multiple Tokens

```python
addresses = ["0xtoken1", "0xtoken2", "0xtoken3"]

resp = httpx.post(f"{{API}}/v1/security/batch-check",
    json={{"addresses": addresses}})

for result in resp.json().get("results", []):
    status = "🚨" if result.get("is_honeypot") else "✅"
    print(f"{{status}} {{result['address'][:10]}}...")
```

## Red Flags Before You Buy

1. **Sell tax > 10%** — Likely honeypot
2. **Hidden owner** — Contract modifiable post-deployment
3. **No liquidity lock** — Team can drain funds
4. **Copy-paste contract** — Same code as known scams

## Full Token Security Audit

```bash
curl "https://chainsight-api.onrender.com/v1/security/token/0xdAC17F958D2ee523a2206206994597C13D831ec7"
```

Returns: honeypot status, buy/sell tax, owner privileges, contract verification, and risk score.

🔗 [RapidAPI](https://rapidapi.com/storbaz/api/chainsight) | 🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*Part of ChainSight — free crypto security tools for developers.*"""

    elif topic == "multi_asset":
        body = f"""## The Fragmentation Problem

Most developers use 3+ APIs for financial data: CoinGecko for crypto, Alpha Vantage for forex, Yahoo Finance for stocks. Three rate limits, three billing accounts, three SDKs.

**Current Market:** Fear & Greed at **{fv}/100** ({fc})

{coins_md}

## One API, All Assets

The ChainSight API unifies crypto, forex, stocks, and commodities:

```bash
curl "https://chainsight-api.onrender.com/v1/forex/overview"
```

```json
{{
  "forex": [
    {{"symbol": "EUR/USD", "rate": 1.1435, "change_pct": 0.12}},
    {{"symbol": "GBP/USD", "rate": 1.3251, "change_pct": -0.08}},
    {{"symbol": "USD/JPY", "rate": 148.92, "change_pct": 0.31}}
  ],
  "stocks": [
    {{"symbol": "SPY", "price": 589.73, "change_pct": 0.45}},
    {{"symbol": "AAPL", "price": 214.29, "change_pct": 1.23}},
    {{"symbol": "NVDA", "price": 135.40, "change_pct": -0.67}}
  ],
  "commodities": [
    {{"symbol": "Gold", "price": 3341.60, "change_pct": 0.31}},
    {{"symbol": "Oil", "price": 80.75, "change_pct": -0.22}}
  ]
}}
```

## Build a Dashboard in 10 Lines

```python
import httpx

API = "https://chainsight-api.onrender.com"

data = httpx.get(f"{{API}}/v1/forex/overview").json()

print("=== FOREX ===")
for p in data["forex"]:
    print(f"{{p['symbol']}}: {{p['rate']}}")

print("\\n=== STOCKS ===")
for s in data["stocks"]:
    print(f"{{s['symbol']}}: ${{s['price']}}")
```

## Historical Data

```python
# Get 3 months of EUR/USD data
resp = httpx.get(f"{{API}}/v1/forex/history",
    params={{"symbol": "EUR/USD", "range": "3mo", "interval": "1wk"}})

for candle in resp.json().get("candles", []):
    print(f"{{candle['date']}}: O={{candle['open']}} H={{candle['high']}} L={{candle['low']}} C={{candle['close']}}")
```

## Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `/v1/forex/rates` | ECB currency rates (13 pairs) |
| `/v1/forex/pairs` | All available symbols |
| `/v1/forex/history` | Historical OHLC via Yahoo Finance |
| `/v1/forex/overview` | Forex + stocks + commodities |
| `/v1/forex/search` | Search any symbol |

## Free Tier

No credit card required. 100 requests/day.

🔗 [RapidAPI](https://rapidapi.com/storbaz/api/chainsight) | 🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*ChainSight — unified financial data for developers.*"""

    else:
        body = f"""## Overview

{coins_md}

**Fear & Greed Index:** {fv}/100 ({fc})

## Getting Started

The ChainSight API provides free access to crypto market data, whale tracking, security analysis, forex rates, and more.

```bash
# Top 5 cryptocurrencies
curl "https://chainsight-api.onrender.com/v1/market/top?limit=5"

# Fear & Greed Index
curl "https://chainsight-api.onrender.com/v1/market/fear-greed"

# Forex rates
curl "https://chainsight-api.onrender.com/v1/forex/rates?base=EUR&symbols=USD,GBP"
```

## 30+ Endpoints

- **Market Data** — Prices, trending, global metrics, correlation
- **Whale Tracking** — 9 chains, real-time large transactions
- **Security** — Honeypot detection, token audits (Pro)
- **Signals** — RSI/MACD momentum, volume anomaly (Pro)
- **Forex & Stocks** — ECB rates, Yahoo Finance historical
- **DeFi** — Protocol TVL, yield comparison, stablecoins
- **News** — Aggregated from CoinTelegraph, CryptoNews, Bitcoin Magazine
- **Widgets** — Embeddable JS widgets for any website

🔗 [RapidAPI](https://rapidapi.com/storbaz/api/chainsight) | 🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*Free tier available. No credit card. Open source.*"""

    return body


async def get_market_data():
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r1 = await client.get(f"{CHAINSIGHT_BASE}/v1/market/top", params={"limit": 5})
            top = r1.json()
        except Exception:
            top = []
        try:
            r2 = await client.get(f"{CHAINSIGHT_BASE}/v1/market/fear-greed")
            fg = r2.json()
        except Exception:
            fg = {"value": 50, "classification": "Neutral"}
        return top, fg


def get_article_index() -> int:
    try:
        with open("/tmp/devto_index.json") as f:
            return json.load(f).get("idx", 0)
    except Exception:
        return 0


def save_article_index(idx: int):
    with open("/tmp/devto_index.json", "w") as f:
        json.dump({"idx": idx}, f)


def get_last_publish_date() -> str:
    try:
        with open("/tmp/devto_last_publish.json") as f:
            return json.load().get("date", "")
    except Exception:
        return ""


def save_last_publish_date(date_str: str):
    with open("/tmp/devto_last_publish.json", "w") as f:
        json.dump({"date": date_str}, f)


async def publish_next() -> dict:
    if not DEVTO_API_KEY:
        return {"error": "DEVTO_API_KEY not set"}

    last_date = get_last_publish_date()
    if last_date:
        from datetime import timedelta
        import random
        last = datetime.strptime(last_date, "%Y-%m-%d")
        days_since = (datetime.utcnow() - last).days
        min_days = random.randint(1, 3)
        if days_since < min_days:
            return {"status": "skipped", "reason": f"Published {days_since}d ago, min {min_days}d"}

    idx = get_article_index()
    topic_data = ARTICLES[idx % len(ARTICLES)]

    top_coins, fear_greed = await get_market_data()
    body_md = build_article(topic_data, top_coins, fear_greed)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{DEVTO_API}/articles",
            headers={"api-key": DEVTO_API_KEY, "Content-Type": "application/json"},
            json={"article": {
                "title": topic_data["title"],
                "body_markdown": body_md,
                "tags": ",".join(topic_data["tags"]),
                "published": True,
            }},
        )

    save_article_index(idx + 1)
    save_last_publish_date(datetime.utcnow().strftime("%Y-%m-%d"))

    if resp.status_code in (200, 201):
        data = resp.json()
        return {
            "status": "published",
            "title": topic_data["title"],
            "url": data.get("url", ""),
            "id": data.get("id", ""),
        }
    return {"error": resp.status_code, "detail": resp.text[:200]}
