"""ChainSight MCP Server — HTTP transport for public access."""

from __future__ import annotations
import os
from typing import Annotated

import httpx
from fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP(
    name="chainsight",
    instructions="Crypto intelligence tools. Use get_top_coins for market data, "
                 "get_coin_detail for specific tokens, get_fear_greed for sentiment, "
                 "get_defi_protocols for DeFi TVL, and get_whale_transactions for on-chain activity.",
    version="1.0.0",
)

CHAINSIGHT_BASE = os.environ.get("CHAINSIGHT_BASE_URL", "https://chainsight-api.onrender.com")


@mcp.tool(
    tags={"crypto", "market", "price"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_top_coins(
    limit: Annotated[int, Field(description="Number of coins (1-250)", ge=1, le=250)] = 20,
    currency: Annotated[str, Field(description="Price currency (usd, eur, btc)")] = "usd",
) -> dict:
    """Get top cryptocurrencies ranked by market cap with real-time prices."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/market/top",
            params={"limit": limit, "currency": currency},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "coin", "detail"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_coin_detail(
    coin_id: Annotated[str, Field(description="Coin ID (e.g., bitcoin, ethereum, solana)")],
    currency: Annotated[str, Field(description="Price currency")] = "usd",
) -> dict:
    """Get detailed data for a specific cryptocurrency including price, supply, ATH, and changes."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/market/coin/{coin_id}",
            params={"currency": currency},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "search"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def search_coins(
    query: Annotated[str, Field(description="Search term (name or symbol)")],
) -> dict:
    """Search for cryptocurrencies by name or symbol."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/market/search",
            params={"query": query},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "market", "global"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_global_market() -> dict:
    """Get global crypto market data: total market cap, volume, dominance percentages."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/global")
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "sentiment", "fear", "greed"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_fear_greed_index() -> dict:
    """Get the current Crypto Fear & Greed Index (0-100). Used for market sentiment analysis."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/fear-greed")
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "sentiment", "history"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_fear_greed_history(
    limit: Annotated[int, Field(description="Number of days (1-365)", ge=1, le=365)] = 30,
) -> dict:
    """Get historical Fear & Greed Index values for trend analysis."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/market/fear-greed/history",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "defi", "tvl"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_defi_protocols(
    limit: Annotated[int, Field(description="Number of protocols (1-100)", ge=1, le=100)] = 20,
) -> dict:
    """Get top DeFi protocols ranked by Total Value Locked (TVL)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/defi/protocols",
            params={"limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "defi", "yields"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_defi_yields(
    chain: Annotated[str | None, Field(description="Filter by chain (Ethereum, Arbitrum, etc.)")] = None,
    limit: Annotated[int, Field(description="Number of pools (1-100)", ge=1, le=100)] = 20,
) -> dict:
    """Get top DeFi yield opportunities across chains with APY and TVL data."""
    async with httpx.AsyncClient(timeout=15) as client:
        params = {"limit": limit}
        if chain:
            params["chain"] = chain
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/defi/yields",
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "defi", "stablecoins"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_stablecoins() -> dict:
    """Get top stablecoins ranked by circulating supply with chain distribution."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/defi/stablecoins")
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "whales", "ethereum"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_whale_transactions(
    min_value: Annotated[float, Field(description="Minimum ETH value", ge=1)] = 100,
) -> dict:
    """Get large ETH transactions above a threshold. Useful for whale tracking."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CHAINSIGHT_BASE}/v1/whales/eth",
            params={"min_value": min_value},
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool(
    tags={"crypto", "gas", "ethereum"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
)
async def get_gas_estimate() -> dict:
    """Get current Ethereum gas prices in Gwei (low, average, fast)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/whales/gas")
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
