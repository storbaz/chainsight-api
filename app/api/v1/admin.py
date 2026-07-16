from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.middleware.api_key import create_api_key, list_api_keys, revoke_api_key, PLANS

router = APIRouter(prefix="/admin", tags=["Admin"])


class CreateKeyRequest(BaseModel):
    label: str = ""
    plan: str = "free"


@router.post("/keys")
async def create_key(body: CreateKeyRequest):
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Choose: {list(PLANS.keys())}")
    return create_api_key(label=body.label, plan=body.plan)


@router.get("/keys")
async def get_keys():
    return list_api_keys()


@router.delete("/keys/{key}")
async def delete_key(key: str):
    if revoke_api_key(key):
        return {"revoked": True, "key": key}
    raise HTTPException(status_code=404, detail="Key not found")
