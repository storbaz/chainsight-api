"""Hashnode auto-publisher — generates and posts crypto articles via GraphQL API."""

import os
import json
import httpx
from datetime import datetime, timezone

HASHNODE_API_TOKEN = os.environ.get("HASHNODE_API_TOKEN", "")
HASHNODE_PUBLICATION_ID = os.environ.get("HASHNODE_PUBLICATION_ID", "")
HASHNODE_API = "https://gql.hashnode.com"
CHAINSIGHT_BASE = "https://chainsight-api.onrender.com"

ARTICLES = [
    {
        "topic": "whales",
        "title": "Track Crypto Whale Transactions Across 9 Blockchains with One API",
        "tags": ["cryptocurrency", "blockchain", "python", "api"],
        "slug": "track-crypto-whale-transactions-9-blockchains",
    },
    {
        "topic": "honeypot",
        "title": "How to Detect Honeypot Tokens Before They Rug You",
        "tags": ["cryptocurrency", "security", "solidity", "web3"],
        "slug": "detect-honeypot-tokens-before-rug",
    },
    {
        "topic": "multi_asset",
        "title": "Unified Financial API: Crypto, Forex & Stocks in One Endpoint",
        "tags": ["api", "fintech", "python", "cryptocurrency"],
        "slug": "unified-financial-api-crypto-forex-stocks",
    },
    {
        "topic": "fear_greed",
        "title": "Building Smarter Trading Bots with Fear & Greed Index Data",
        "tags": ["trading", "cryptocurrency", "python", "machine-learning"],
        "slug": "smarter-trading-bots-fear-greed-index",
    },
    {
        "topic": "defi",
        "title": "Find the Best DeFi Yield Across 200+ Protocols with One API Call",
        "tags": ["defi", "ethereum", "cryptocurrency", "api"],
        "slug": "best-defi-yield-200-protocols-api",
    },
    {
        "topic": "building_in_public",
        "title": "I Launched a Free Crypto API as a Solo Dev — Here's What Happened",
        "tags": ["startup", "building-in-public", "api", "cryptocurrency"],
        "slug": "launched-free-crypto-api-solo-dev",
    },
    {
        "topic": "bitcoin",
        "title": "Monitor Bitcoin Whale Movements with Blockstream and Python",
        "tags": ["bitcoin", "python", "blockchain", "api"],
        "slug": "monitor-bitcoin-whale-movements-blockstream",
    },
    {
        "topic": "widgets",
        "title": "Embed Real-Time Crypto Data on Any Website in 2 Minutes",
        "tags": ["javascript", "web-development", "cryptocurrency", "api"],
        "slug": "embed-real-time-crypto-data-website-2-minutes",
    },
    {
        "topic": "security",
        "title": "Token Security Audit: Check Any ERC-20 Contract in Seconds",
        "tags": ["ethereum", "security", "solidity", "smart-contracts"],
        "slug": "token-security-audit-erc20-contract-seconds",
    },
    {
        "topic": "signals",
        "title": "Crypto Alpha Signals: RSI, MACD & Volume Anomaly Detection with Python",
        "tags": ["python", "trading", "data-science", "cryptocurrency"],
        "slug": "crypto-alpha-signals-rsi-macd-volume-anomaly",
    },
]


GRAPHQL_CREATE_DRAFT = """
mutation CreateDraft($input: CreateDraftInput!) {
  createDraft(input: $input) {
    draft {
      id
    }
  }
}
"""

GRAPHQL_PUBLISH_DRAFT = """
mutation PublishDraft($input: PublishDraftInput!) {
  publishDraft(input: $input) {
    post {
      url
      id
      slug
    }
  }
}
"""


def build_article_content(topic_data: dict, top_coins: list, fear_greed: dict) -> str:
    fv = fear_greed.get("value", 50)
    fc = fear_greed.get("classification", "Neutral")

    coins_md = ""
    for c in top_coins[:5]:
        ch = c.get("price_change_percentage_24h", 0) or 0
        icon = "📈" if ch >= 0 else "📉"
        coins_md += f"- **{c['name']}** (${c['current_price']:,.2f}) {icon} {ch:+.1f}%\n"

    topic = topic_data["topic"]

    if topic == "whales":
        body = f"""When a whale moves $50M of ETH, the entire market feels it. The question is: can you detect it before everyone else?

**Current Market Snapshot:** Fear & Greed Index at **{fv}/100** ({fc})

{coins_md}

## What Is Whale Tracking?

Whale tracking monitors large cryptocurrency transactions — typically $100K+ moves — across blockchain networks. These transactions often precede significant price movements.

## The Problem with Existing Tools

Most whale trackers are:
- **Expensive** ($50-500/month)
- **Limited to one chain** (usually Ethereum only)
- **Slow** (15-30 min delay)

## The Solution: Multi-Chain API

The ChainSight API tracks whale transactions across **9 blockchains** in real-time:

| Chain | Data Source | Min Trackable |
|-------|------------|---------------|
| Ethereum | Etherscan V2 | 100 ETH |
| Bitcoin | Blockstream Mempool | 1 BTC |
| BSC | Etherscan V2 | 1000 BNB |
| Solana | Solscan RPC | 100 SOL |
| Polygon, Arbitrum, Base, OP, Avalanche | Etherscan V2 | Varies |

## Quick Start

```python
import httpx

API = "https://chainsight-api.onrender.com"

# Get large Ethereum transactions
resp = httpx.get(f"{{API}}/v1/whales/chain/ethereum", params={{"min_value": 100000}})
for tx in resp.json():
    if "hash" in tx:
        print(f"🐋 {{tx['value']}} ETH — {{tx['from_address'][:12]}}...")
```

## Build a Real-Time Whale Alert Bot

```python
import httpx, asyncio

API = "https://chainsight-api.onrender.com"

async def monitor():
    seen = set()
    while True:
        resp = httpx.get(f"{{API}}/v1/whales/chain/ethereum?min_value=500000")
        txs = resp.json()
        for tx in txs:
            h = tx.get("hash")
            if h and h not in seen:
                print(f"🚨 WHALE: {{tx['value']}} ETH moved!")
                seen.add(h)
        await asyncio.sleep(60)

asyncio.run(monitor())
```

## What Can You Build?

- **Trading bots** that react to whale movements in real-time
- **Portfolio alerts** when your tracked wallets move funds
- **Research dashboards** tracking smart money flows
- **Risk management** detecting exchange outflows

## Try It Free

```bash
curl "https://chainsight-api.onrender.com/v1/whales/chain/ethereum?min_value=100000"
```

No API key required for the free tier.

🔗 [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) | [GitHub](https://github.com/storbaz/chainsight-api)

---
*ChainSight is open source and free for developers.*"""

    elif topic == "honeypot":
        body = f"""Over $12 billion was lost to crypto scams in 2024-2025. Honeypot tokens — contracts that let you buy but never sell — are among the most common traps.

**Current Market:** Fear & Greed at **{fv}/100** ({fc})

{coins_md}

## What Is a Honeypot Token?

A honeypot is a smart contract designed to trick investors:
- You can **buy** the token (the contract allows it)
- You **cannot sell** (hidden restrictions)
- Sell taxes of 99%+
- Blacklist functions
- Owner-only trading

## How to Detect Honeypots

```python
import httpx

API = "https://chainsight-api.onrender.com"

def check_token(address: str):
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

## Red Flags Before You Buy

1. **Sell tax > 10%** — Almost certainly a honeypot
2. **Hidden owner** — Contract can be modified after deployment
3. **No liquidity lock** — Team can drain funds at any time
4. **Copy-paste contract** — Same code as known scams

## Batch Check Multiple Tokens

```python
import httpx

API = "https://chainsight-api.onrender.com"

# Check multiple tokens at once
resp = httpx.post(f"{{API}}/v1/security/batch-check", json={{
    "addresses": [
        {"address": "0xtoken1", "chain": "ethereum"},
        {"address": "0xtoken2", "chain": "bsc"}
    ]
}})
```

## Try It Free

```bash
curl "https://chainsight-api.onrender.com/v1/security/honeypot/0xdAC17F958D2ee523a2206206994597C13D831ec7"
```

🔗 [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) | [GitHub](https://github.com/storbaz/chainsight-api)

---
*Free security tools for crypto developers.*"""

    else:
        body = f"""## Market Overview

{coins_md}

**Fear & Greed Index:** {fv}/100 ({fc})

## Getting Started

The ChainSight API provides free access to crypto market data, whale tracking, security analysis, forex rates, and more — all from a single endpoint.

```bash
# Top 5 cryptocurrencies
curl "https://chainsight-api.onrender.com/v1/market/top?limit=5"

# Fear & Greed Index
curl "https://chainsight-api.onrender.com/v1/market/fear-greed"

# Forex rates
curl "https://chainsight-api.onrender.com/v1/forex/rates?base=EUR&symbols=USD,GBP"
```

## 30+ Endpoints Available

| Category | Endpoints | Free? |
|----------|-----------|-------|
| Market Data | Prices, trending, global, correlation | ✅ |
| Whale Tracking | 9 chains, real-time large transactions | ✅ |
| DeFi | Protocol TVL, yields, stablecoins | ✅ |
| Forex & Stocks | ECB rates, Yahoo Finance historical | ✅ |
| News | Aggregated from top crypto sources | ✅ |
| Security | Honeypot detection, token audits | Pro |
| Signals | RSI/MACD, volume anomaly, whale accumulation | Pro |

## Quick Python Example

```python
import httpx

API = "https://chainsight-api.onrender.com"

# Get top coins
top = httpx.get(f"{{API}}/v1/market/top?limit=5").json()
for coin in top:
    print(f"{{coin['name']}}: ${{coin['current_price']:,.2f}}")

# Get forex overview
overview = httpx.get(f"{{API}}/v1/forex/overview").json()
for p in overview["forex"][:3]:
    print(f"{{p['symbol']}}: {{p['rate']}}")
```

## Try It

```bash
curl "https://chainsight-api.onrender.com/v1/market/top?limit=5"
```

🔗 [ChainSight API](https://rapidapi.com/storbaz/api/chainsight) | [GitHub](https://github.com/storbaz/chainsight-api)

---
*Free tier available. No credit card required. Open source.*"""

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
        with open("/tmp/hashnode_index.json") as f:
            return json.load(f).get("idx", 0)
    except Exception:
        return 0


def save_article_index(idx: int):
    with open("/tmp/hashnode_index.json", "w") as f:
        json.dump({"idx": idx}, f)


def get_last_publish_date() -> str:
    try:
        with open("/tmp/hashnode_last_publish.json") as f:
            return json.load(f).get("date", "")
    except Exception:
        return ""


def save_last_publish_date(date_str: str):
    with open("/tmp/hashnode_last_publish.json", "w") as f:
        json.dump({"date": date_str}, f)


async def publish_next() -> dict:
    if not HASHNODE_API_TOKEN:
        return {"error": "HASHNODE_API_TOKEN not set"}
    if not HASHNODE_PUBLICATION_ID:
        return {"error": "HASHNODE_PUBLICATION_ID not set"}

    last_date = get_last_publish_date()
    if last_date:
        import random
        last = datetime.strptime(last_date, "%Y-%m-%d")
        days_since = (datetime.now(timezone.utc) - last).days
        min_days = random.randint(2, 4)
        if days_since < min_days:
            return {"status": "skipped", "reason": f"Published {days_since}d ago, min {min_days}d"}

    idx = get_article_index()
    topic_data = ARTICLES[idx % len(ARTICLES)]

    top_coins, fear_greed = await get_market_data()
    body_md = build_article_content(topic_data, top_coins, fear_greed)

    tag_objects = [{"name": t, "slug": t.lower().replace(" ", "-")} for t in topic_data["tags"]]

    headers = {
        "Authorization": HASHNODE_API_TOKEN,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Create draft
        draft_resp = await client.post(
            HASHNODE_API,
            headers=headers,
            json={
                "query": GRAPHQL_CREATE_DRAFT,
                "variables": {
                    "input": {
                        "title": topic_data["title"],
                        "contentMarkdown": body_md,
                        "tags": tag_objects,
                        "publicationId": HASHNODE_PUBLICATION_ID,
                    }
                },
            },
        )

        draft_data = draft_resp.json()
        if draft_resp.status_code != 200 or draft_data.get("errors"):
            errors = draft_data.get("errors", [])
            error_msg = errors[0].get("message", draft_resp.text[:200]) if errors else draft_resp.text[:200]
            return {"error": draft_resp.status_code, "detail": f"Draft creation failed: {error_msg}"}

        draft_id = draft_data.get("data", {}).get("createDraft", {}).get("draft", {}).get("id")
        if not draft_id:
            return {"error": "No draft ID returned"}

        # Step 2: Publish draft
        publish_resp = await client.post(
            HASHNODE_API,
            headers=headers,
            json={
                "query": GRAPHQL_PUBLISH_DRAFT,
                "variables": {
                    "input": {
                        "draftId": draft_id,
                    }
                },
            },
        )

    save_article_index(idx + 1)
    save_last_publish_date(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    publish_data = publish_resp.json()
    if publish_resp.status_code == 200 and not publish_data.get("errors"):
        post = publish_data.get("data", {}).get("publishDraft", {}).get("post", {})
        return {
            "status": "published",
            "title": topic_data["title"],
            "url": post.get("url", ""),
            "id": post.get("id", ""),
            "slug": post.get("slug", ""),
        }

    errors = publish_data.get("errors", [])
    error_msg = errors[0].get("message", publish_resp.text[:200]) if errors else publish_resp.text[:200]
    return {"error": publish_resp.status_code, "detail": error_msg}
