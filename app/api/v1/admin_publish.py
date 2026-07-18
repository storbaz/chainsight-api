from fastapi import APIRouter
from app.services.devto_service import publish_next as devto_publish
import os

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/publish-devto")
async def trigger_devto_publish():
    return await devto_publish()


@router.get("/publish-devto")
async def trigger_devto_publish_get():
    return await devto_publish()


@router.get("/publish-hashnode")
async def trigger_hashnode_publish_get():
    try:
        from app.services.hashnode_service import publish_next as hashnode_publish
        return await hashnode_publish()
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.post("/publish-hashnode")
async def trigger_hashnode_publish():
    try:
        from app.services.hashnode_service import publish_next as hashnode_publish
        return await hashnode_publish()
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
