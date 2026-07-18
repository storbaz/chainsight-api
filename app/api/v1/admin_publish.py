from fastapi import APIRouter
from app.services.devto_service import publish_next

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/publish-devto")
async def trigger_publish():
    result = await publish_next()
    return result


@router.get("/publish-devto")
async def trigger_publish_get():
    result = await publish_next()
    return result
