from fastapi import APIRouter, Query, HTTPException
from app.services.whale_service import whale_service
from app.services.chains import CHAINS

router = APIRouter(prefix="/whales", tags=["Whales"])


@router.get("/eth")
async def get_eth_large_transactions(
    min_value: float = Query(100, ge=1, description="Minimum transaction value in USD"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
):
    """Get recent large Ethereum transactions (whale movements)."""
    return await whale_service.get_whale_transactions(chain="ethereum", min_value=min_value, limit=limit)


@router.get("/chain/{chain}")
async def get_chain_whales(
    chain: str,
    min_value: float = Query(100, ge=1, description="Minimum transaction value in USD"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
):
    """Get whale transactions on any supported chain (eth, btc, bsc, sol, polygon, arbitrum, base, optimism, avalanche)."""
    if chain not in CHAINS:
        raise HTTPException(status_code=400, detail=f"Chain '{chain}' not supported. Use: {list(CHAINS.keys())}")
    return await whale_service.get_whale_transactions(chain=chain, min_value=min_value, limit=limit)


@router.get("/gas")
async def get_gas_estimate(
    chain: str = Query("ethereum", description="Chain name or 'all' for all chains"),
):
    """Get current gas prices (low/average/fast) for any EVM chain."""
    if chain == "all":
        return await whale_service.get_all_chains_gas()
    if chain not in CHAINS:
        raise HTTPException(status_code=400, detail=f"Chain '{chain}' not supported. Use: {list(CHAINS.keys())}")
    return await whale_service.get_gas_estimate(chain=chain)


@router.get("/chains")
async def list_chains():
    """List all supported chains with their native token symbols."""
    return [
        {"id": k, "name": v["name"], "symbol": v["symbol"]}
        for k, v in CHAINS.items()
    ]
