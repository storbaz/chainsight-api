from fastapi import APIRouter, Query
from app.services.whale_service import whale_service

router = APIRouter(prefix="/whales", tags=["Whales"])


@router.get("/eth")
async def get_eth_large_transactions(
    min_value: float = Query(100, ge=1),
):
    return await whale_service.get_eth_large_transactions(min_value_eth=min_value)


@router.get("/gas")
async def get_gas_estimate():
    return await whale_service.get_gas_estimate()
