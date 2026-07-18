from fastapi import APIRouter, Query
from app.services.defi_service import defi_service

router = APIRouter(prefix="/defi", tags=["DeFi"])


@router.get("/protocols")
async def get_top_protocols(limit: int = Query(20, ge=1, le=100, description="Number of protocols to return")):
    """Get top DeFi protocols ranked by TVL (Total Value Locked)."""
    return await defi_service.get_top_protocols(limit=limit)


@router.get("/protocols/{protocol_slug}")
async def get_protocol_tvl(protocol_slug: str):
    """Get detailed TVL data for a specific DeFi protocol."""
    return await defi_service.get_protocol_tvl(protocol_slug=protocol_slug)


@router.get("/yields")
async def get_yields(
    chain: str | None = Query(None, description="Filter by chain (e.g. 'Ethereum', 'BSC')"),
    limit: int = Query(20, ge=1, le=100, description="Number of pools to return"),
):
    """Get top DeFi yield pools with APY, TVL, and chain info."""
    return await defi_service.get_yields(chain=chain, limit=limit)


@router.get("/stablecoins")
async def get_stablecoins():
    """Get stablecoin market data: market cap, volume, peg deviations."""
    return await defi_service.get_stablecoins()
