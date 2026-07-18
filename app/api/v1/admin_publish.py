from fastapi import APIRouter
from app.services.devto_service import publish_next as devto_publish

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/publish-devto")
async def trigger_devto_publish():
    return await devto_publish()


@router.get("/publish-devto")
async def trigger_devto_publish_get():
    return await devto_publish()
