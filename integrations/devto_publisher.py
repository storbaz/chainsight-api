"""DEV.to auto-publisher — generates and posts crypto articles weekly."""

import os
import json
import httpx
from datetime import datetime, timedelta

DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")
DEVTO_API = "https://dev.to/api"
CHAINSIGHT_BASE = "https://chainsight-api.onrender.com"
client = httpx.AsyncClient(timeout=30)

ARTICLE_TEMPLATES = [
    {
        "topic": "crypto_whales",
        "title_template": "Whale Watching: How to Track Large Crypto Transactions in Real-Time",
        "tags": ["crypto", "blockchain", "defi", "web3", "api"],
    },
    {
        "topic": "honeypot",
        "title_template": "How to Detect Honeypot Tokens Before You Buy — A Developer's Guide",
        "tags": ["crypto", "security", "solidity", "web3", "api"],
    },
    {
        "topic": "forex_stocks",
        "title_template": "Building a Multi-Asset Dashboard: Crypto, Forex & Stocks in One API Call",
        "tags": ["python", "api", "finance", "crypto", "building-in-public"],
    },
    {
        "topic": "fear_greed",
        "title_template": "Using Fear & Greed Index Data to Build Smarter Trading Bots",
        "tags": ["python", "crypto", "trading", "api", "fintech"],
    },
    {
        "topic": "defi_yields",
        "title_template": "DeFi Yield Farming Data: How to Find the Best APY Across Protocols",
        "tags": ["defi", "crypto", "ethereum", "api", "web3"],
    },
    {
        "topic": "portfolio",
        "title_template": "I Built a Free Crypto Portfolio Tracker API — Here's What I Learned",
        "tags": ["crypto", "building-in-public", "api", "javascript", "startup"],
    },
    {
        "topic": "bitcoin_tracking",
        "title_template": "Track Bitcoin Whale Movements with Blockstream API and Python",
        "tags": ["bitcoin", "python", "blockchain", "api", "data-engineering"],
    },
    {
        "topic": "embeddable_widgets",
        "title_template": "How to Embed Real-Time Crypto Data on Any Website (Free Widget)",
        "tags": ["javascript", "crypto", "web-development", "api", "widgets"],
    },
]


def generate_article(topic_data: dict, market_data: dict, fear_greed: dict) -> str:
    topic = topic_data["topic"]
    fear_val = fear_greed.get("value", 50)
    fear_cls = fear_greed.get("classification", "Neutral")
    top_coins = market_data.get("top", [])[:5]

    coins_section = ""
    for c in top_coins:
        ch = c.get("price_change_percentage_24h", 0) or 0
        arrow = "📈" if ch >= 0 else "📉"
        coins_section += f"- **{c['name']}** (${c['current_price']:,.2f}) {arrow} {ch:+.1f}%\n"

    if topic == "crypto_whales":
        return f"""---
title: {topic_data['title_template']}
published: true
description: Learn how to monitor large cryptocurrency transactions across 9 blockchain networks using free APIs.
tags: {json.dumps(topic_data['tags'][:4])}
---

# Track Crypto Whales in Real-Time

The cryptocurrency market moves when whales move. A single $10M ETH transfer can signal a major price shift. Here's how to track these movements programmatically.

## Current Market Snapshot

**Fear & Greed Index:** {fear_val}/100 ({fear_cls})

{coins_section}

## What Are Whale Transactions?

Whale transactions are blockchain transfers exceeding a threshold you define (typically $100K+). These large movements often precede significant market events.

## How to Track Them

The [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) provides real-time whale data across 9 chains:

```
GET /v1/whales/chain/ethereum?min_value=100000
```

This returns large ETH transactions with sender, receiver, amount, and gas data.

### Supported Chains
- **Ethereum** — Via Etherscan V2 API
- **Bitcoin** — Via Blockstream mempool API
- **BSC, Polygon, Arbitrum, Base, Optimism, Avalanche** — Via Etherscan V2
- **Solana** — Via Solscan API

## Building a Whale Alert Bot

```python
import httpx

API = "https://chainsight-api.onrender.com"

async def check_whales():
    resp = await httpx.get(f"{{API}}/v1/whales/chain/ethereum", params={{"min_value": 500000}})
    txs = resp.json()
    for tx in txs:
        if "hash" in tx:
            print(f"🐋 {{tx['value']}} ETH — {{tx['from_address'][:10]}}...")
```

## Why This Matters

Whale tracking isn't just for hedge funds. Independent traders can use this data to:
- Avoid buying right before a dump
- Identify accumulation phases
- Track institutional money flow

## Try It Free

The ChainSight API offers a free tier with 100 requests/day. No credit card needed.

🔗 [Try on RapidAPI](https://rapidapi.com/storbaz/api/chainsight)
🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*Built by a solo developer. Open source. Free tier available.*"""

    elif topic == "honeypot":
        return f"""---
title: {topic_data['title_template']}
published: true
description: A practical guide to detecting honeypot tokens and rug pulls before investing your crypto.
tags: {json.dumps(topic_data['tags'][:4])}
---

# How to Detect Honeypot Tokens Before You Buy

In 2024-2025, over $12 billion was lost to crypto scams. Honeypot tokens — contracts that let you buy but not sell — are one of the most common traps. Here's how to detect them programmatically.

## Current Market

**Fear & Greed Index:** {fear_val}/100 ({fear_cls})

{coins_section}

## What Is a Honeypot?

A honeypot token is a smart contract designed to trick investors. You can buy the token, but when you try to sell, the transaction fails due to hidden mechanisms:

- Hidden sell taxes (99%+)
- Blacklist functions
- Owner-only trading
- Proxy contracts that can change rules

## Detecting Honeypots with Code

The [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) integrates with GoPlus Security to analyze any token contract:

```
GET /v1/security/honeypot/0xTokenAddress
```

### Response

```json
{{
  "is_honeypot": false,
  "risk_level": "low",
  "buy_tax": 0,
  "sell_tax": 0,
  "owner_can_sell": true,
  "hidden_owner": false,
  "can_take_back_ownership": false
}}
```

## Building a Pre-Purchase Checker

```python
import httpx

API = "https://chainsight-api.onrender.com"

async def check_token(address: str):
    resp = await httpx.get(f"{{API}}/v1/security/honeypot/{{address}}")
    data = resp.json()

    if data.get("is_honeypot"):
        print("🚨 HONEYYPOT DETECTED — Do not buy!")
        return

    risk = data.get("risk_level", "unknown")
    buy_tax = data.get("buy_tax", 0)
    sell_tax = data.get("sell_tax", 0)

    if risk == "high" or sell_tax > 10:
        print(f"⚠️ High risk — Sell tax: {{sell_tax}}%")
    else:
        print(f"✅ Looks safe — Risk: {{risk}}")
```

## Red Flags to Watch

1. **Sell tax > 10%** — Likely a honeypot
2. **Hidden owner** — Contract can be modified after deployment
3. **No liquidity lock** — Team can drain liquidity
4. **Copy-paste contract** — Same code as known scams

## Try It Free

```bash
curl "https://chainsight-api.onrender.com/v1/security/honeypot/0xdAC17F958D2ee523a2206206994597C13D831ec7"
```

The security endpoints are available on the Pro plan. [Try free on RapidAPI](https://rapidapi.com/storbaz/api/chainsight).

---
*Part of the [ChainSight API](https://github.com/storbaz/chainsight-api) — open source crypto intelligence.*"""

    elif topic == "forex_stocks":
        return f"""---
title: {topic_data['title_template']}
published: true
description: How to build a unified dashboard for crypto, forex pairs, and stock data using a single free API.
tags: {json.dumps(topic_data['tags'][:4])}
---

# Building a Multi-Asset Dashboard: Crypto, Forex & Stocks

Most financial data APIs force you to use separate services for crypto, forex, and stocks. Here's how to unify everything in one API call.

## The Problem

- CoinGecko for crypto
- Alpha Vantage for forex
- Yahoo Finance API for stocks

Three APIs, three rate limits, three billing accounts. There's a better way.

## The Solution: Unified API

The [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) combines crypto, forex, and stock data in a single endpoint:

```
GET /v1/forex/overview
```

### Response

```json
{{
  "forex": [
    {{"symbol": "EUR/USD", "rate": 1.1435, "change_pct": 0.12}},
    {{"symbol": "GBP/USD", "rate": 1.3251, "change_pct": -0.08}}
  ],
  "stocks": [
    {{"symbol": "SPY", "price": 589.73, "change_pct": 0.45}},
    {{"symbol": "AAPL", "price": 214.29, "change_pct": 1.23}}
  ],
  "commodities": [
    {{"symbol": "GC=F", "price": 3341.60, "change_pct": 0.31}}
  ]
}}
```

## Available Data

| Asset Class | Coverage | Source |
|------------|----------|--------|
| Crypto | 15,000+ coins | CoinGecko + CoinPaprika |
| Forex | 13 major pairs | ECB (Frankfurter API) |
| Stocks | SPY, QQQ, AAPL, TSLA, NVDA... | Yahoo Finance |
| Commodities | Gold, Silver, Oil | Yahoo Finance |

## Build a Dashboard

```python
import httpx

API = "https://chainsight-api.onrender.com"

async def get_overview():
    resp = await httpx.get(f"{{API}}/v1/forex/overview")
    data = resp.json()

    for pair in data["forex"]:
        print(f"{{pair['symbol']}}: {{pair['rate']}}")

    for stock in data["stocks"]:
        print(f"{{stock['symbol']}}: ${{stock['price']}}")
```

## Try It

```bash
curl "https://chainsight-api.onrender.com/v1/forex/overview"
curl "https://chainsight-api.onrender.com/v1/forex/history?symbol=AAPL&range=1mo"
curl "https://chainsight-api.onrender.com/v1/forex/rates?base=EUR&symbols=USD,GBP,JPY"
```

Free tier available. [Get started on RapidAPI](https://rapidapi.com/storbaz/api/chainsight).

---
*Part of [ChainSight](https://github.com/storbaz/chainsight-api) — unified financial data API.*"""

    else:
        return f"""---
title: {topic_data['title_template']}
published: true
description: Exploring crypto market tools and free APIs for developers.
tags: {json.dumps(topic_data['tags'][:4])}
---

# {topic_data['title_template']}

## Current Market

**Fear & Greed Index:** {fear_val}/100 ({fear_cls})

{coins_section}

## Getting Started

The [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) provides free access to crypto market data, whale tracking, security analysis, and more.

```bash
curl "https://chainsight-api.onrender.com/v1/market/top?limit=5"
```

## Try It Free

🔗 [RapidAPI](https://rapidapi.com/storbaz/api/chainsight)
🔗 [GitHub](https://github.com/storbaz/chainsight-api)

---
*Open source. Free tier. No credit card.*"""


async def fetch_market_data() -> dict:
    data = {}
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/top", params={"limit": 5})
        data["top"] = resp.json()
    except Exception:
        data["top"] = []
    return data


async def fetch_fear_greed() -> dict:
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/fear-greed")
        return resp.json()
    except Exception:
        return {"value": 50, "classification": "Neutral"}


async def publish_to_devto(article_md: str, api_key: str) -> dict:
    resp = await client.post(
        f"{DEVTO_API}/articles",
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "article": {
                "body_markdown": article_md,
                "published": True,
            }
        },
    )
    if resp.status_code in (200, 201):
        return resp.json()
    return {"error": resp.status_code, "detail": resp.text}


async def get_next_article_index() -> int:
    index_file = "/tmp/devto_article_index.json"
    try:
        with open(index_file) as f:
            data = json.load(f)
            return data.get("next_index", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


async def save_article_index(index: int):
    index_file = "/tmp/devto_article_index.json"
    with open(index_file, "w") as f:
        json.dump({"next_index": index}, f)


async def generate_and_publish(api_key: str) -> dict:
    idx = await get_next_article_index()
    topic_data = ARTICLE_TEMPLATES[idx % len(ARTICLE_TEMPLATES)]

    market_data = await fetch_market_data()
    fear_greed = await fetch_fear_greed()

    article_md = generate_article(topic_data, market_data, fear_greed)

    result = await publish_to_devto(article_md, api_key)

    await save_article_index(idx + 1)

    return {
        "topic": topic_data["topic"],
        "title": topic_data["title_template"],
        "result": result,
    }


if __name__ == "__main__":
    import asyncio
    key = os.environ.get("DEVTO_API_KEY", "")
    if not key:
        print("Set DEVTO_API_KEY env var first")
    else:
        result = asyncio.run(generate_and_publish(key))
        print(json.dumps(result, indent=2))
