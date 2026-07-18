from fastapi import APIRouter, Query, HTTPException
from app.services.security_service import security_service

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/honeypot/{address}")
async def check_honeypot(
    address: str,
    chain: str = Query("ethereum", description="Chain: ethereum, bsc, polygon, arbitrum, base"),
):
    """Check if a token is a honeypot (can buy but can't sell). Returns buy/sell tax, risk level, and flags."""
    result = await security_service.check_honeypot(address=address, chain=chain)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/token/{address}")
async def token_security(
    address: str,
    chain: str = Query("ethereum", description="Chain: ethereum, bsc, polygon, arbitrum, base"),
):
    """Full security audit for a token: contract verification, ownership, holder distribution, risk score."""
    result = await security_service.get_token_security(address=address, chain=chain)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/batch-check")
async def batch_security_check(
    addresses: list[dict],
):
    """Batch honeypot check for multiple tokens. Send JSON array of {\"address\": \"0x...\", \"chain\": \"ethereum\"}."""
    if not addresses:
        raise HTTPException(status_code=400, detail="Provide list of {address, chain} objects")
    return await security_service.batch_security_check(addresses=addresses)
