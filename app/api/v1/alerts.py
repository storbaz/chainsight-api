from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, HttpUrl
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class CreateAlertRequest(BaseModel):
    webhook_url: str
    alert_type: str = "whale_transfer"
    threshold: float = 100
    chain: str = "ethereum"
    label: str = ""


@router.post("/webhook")
async def create_webhook_alert(body: CreateAlertRequest):
    if not body.webhook_url.startswith("http"):
        raise HTTPException(status_code=400, detail="webhook_url must be a valid URL")
    if body.threshold < 1:
        raise HTTPException(status_code=400, detail="threshold must be >= 1")
    return alert_service.create_alert(
        webhook_url=body.webhook_url,
        alert_type=body.alert_type,
        threshold=body.threshold,
        chain=body.chain,
        label=body.label,
    )


@router.get("/webhook")
async def list_webhook_alerts():
    return alert_service.list_alerts()


@router.delete("/webhook/{alert_id}")
async def delete_webhook_alert(alert_id: str):
    if alert_service.delete_alert(alert_id):
        return {"deleted": True, "alert_id": alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.patch("/webhook/{alert_id}/toggle")
async def toggle_webhook_alert(alert_id: str):
    result = alert_service.toggle_alert(alert_id)
    if result:
        return result
    raise HTTPException(status_code=404, detail="Alert not found")
