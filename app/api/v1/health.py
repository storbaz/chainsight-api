from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {
            "coingecko": "connected",
            "defillama": "connected",
            "etherscan": "connected",
            "fear_greed": "connected",
        },
    }
