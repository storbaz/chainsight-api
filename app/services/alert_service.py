import json
import asyncio
import httpx
from pathlib import Path

ALERTS_FILE = Path(__file__).parent.parent.parent / "data" / "alerts.json"
http_client = httpx.AsyncClient(timeout=10)


def _load_alerts() -> list[dict]:
    try:
        if ALERTS_FILE.exists():
            return json.loads(ALERTS_FILE.read_text())
    except Exception:
        pass
    return []


def _save_alerts(alerts: list[dict]):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2))


class AlertService:

    def create_alert(
        self,
        webhook_url: str,
        alert_type: str,
        threshold: float = 100,
        chain: str = "ethereum",
        label: str = "",
    ) -> dict:
        alerts = _load_alerts()
        alert_id = f"alert_{len(alerts) + 1}"
        alert = {
            "id": alert_id,
            "webhook_url": webhook_url,
            "alert_type": alert_type,
            "threshold": threshold,
            "chain": chain,
            "label": label,
            "active": True,
            "created_at": str(asyncio.get_event_loop().time()),
            "trigger_count": 0,
        }
        alerts.append(alert)
        _save_alerts(alerts)
        return alert

    def list_alerts(self) -> list[dict]:
        return _load_alerts()

    def delete_alert(self, alert_id: str) -> bool:
        alerts = _load_alerts()
        before = len(alerts)
        alerts = [a for a in alerts if a["id"] != alert_id]
        if len(alerts) < before:
            _save_alerts(alerts)
            return True
        return False

    def toggle_alert(self, alert_id: str) -> dict | None:
        alerts = _load_alerts()
        for a in alerts:
            if a["id"] == alert_id:
                a["active"] = not a["active"]
                _save_alerts(alerts)
                return a
        return None

    async def check_and_trigger(self, transactions: list[dict], alerts: list[dict] | None = None):
        if alerts is None:
            alerts = _load_alerts()

        active = [a for a in alerts if a.get("active") and a.get("alert_type") == "whale_transfer"]
        if not active:
            return

        triggered = []
        for tx in transactions:
            if isinstance(tx, dict) and "value" in tx:
                value = tx["value"]
                for alert in active:
                    if value >= alert.get("threshold", 100):
                        payload = {
                            "alert_id": alert["id"],
                            "type": "whale_transfer",
                            "threshold": alert["threshold"],
                            "transaction": tx,
                            "label": alert.get("label", ""),
                        }
                        try:
                            resp = await http_client.post(
                                alert["webhook_url"],
                                json=payload,
                                timeout=5,
                            )
                            if resp.status_code < 300:
                                triggered.append(alert["id"])
                                alerts_list = _load_alerts()
                                for a in alerts_list:
                                    if a["id"] == alert["id"]:
                                        a["trigger_count"] = a.get("trigger_count", 0) + 1
                                _save_alerts(alerts_list)
                        except Exception:
                            pass
        return triggered


alert_service = AlertService()
