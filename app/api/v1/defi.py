from fastapi import APIRouter, Query
from app.services.defi_service import defi_service

router = APIRouter(prefix="/defi", tags=["DeFi"])


@router.get("/protocols")
async def get_top_protocols(limit: int = Query(20, ge=1, le=100)):
    return await defi_service.get_top_protocols(limit=limit)


@router.get("/protocols/{protocol_slug}")
async def get_protocol_tvl(protocol_slug: str):
    return await defi_service.get_protocol_tvl(protocol_slug=protocol_slug)


@router.get("/yields")
async def get_yields(
    chain: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    return await defi_service.get_yields(chain=chain, limit=limit)


@router.get("/stablecoins")
async def get_stablecoins():
    return await defi_service.get_stablecoins()
