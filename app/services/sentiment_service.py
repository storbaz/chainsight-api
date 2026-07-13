import httpx
from app.config import settings


class SentimentService:

    async def get_fear_greed_index(self) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(settings.FEAR_GREED_URL, params={"limit": 1})
            resp.raise_for_status()
            data = resp.json().get("data", [{}])[0]
            return {
                "value": int(data.get("value", 0)),
                "classification": data.get("value_classification", ""),
                "timestamp": data.get("timestamp", ""),
                "time_until_update": data.get("time_until_update"),
            }

    async def get_fear_greed_history(self, limit: int = 30) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(settings.FEAR_GREED_URL, params={"limit": limit})
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [
                {
                    "value": int(item.get("value", 0)),
                    "classification": item.get("value_classification", ""),
                    "timestamp": item.get("timestamp", ""),
                }
                for item in data
            ]


sentiment_service = SentimentService()
