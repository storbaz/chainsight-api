import json
import time
from pathlib import Path
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

KEYS_FILE = Path(__file__).parent.parent.parent / "data" / "api_keys.json"

PLANS = {
    "free": {"requests_per_day": 100, "rate_limit_per_min": 10},
    "pro": {"requests_per_day": -1, "rate_limit_per_min": 60},
}

USAGE_FILE = Path(__file__).parent.parent.parent / "data" / "usage.json"


def _load_keys() -> dict:
    try:
        if KEYS_FILE.exists():
            return json.loads(KEYS_FILE.read_text())
    except Exception:
        pass
    return {}


def _load_usage() -> dict:
    try:
        if USAGE_FILE.exists():
            return json.loads(USAGE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_usage(usage: dict):
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(usage, indent=2))
    except Exception:
        pass


def create_api_key(label: str = "", plan: str = "free") -> dict:
    import secrets
    keys = _load_keys()
    key = f"cs_{secrets.token_hex(24)}"
    entry = {
        "key": key,
        "label": label,
        "plan": plan,
        "active": True,
        "created_at": int(time.time()),
    }
    keys[key] = entry
    try:
        KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEYS_FILE.write_text(json.dumps(keys, indent=2))
    except Exception:
        pass
    return entry


def list_api_keys() -> list[dict]:
    return list(_load_keys().values())


def revoke_api_key(key: str) -> bool:
    keys = _load_keys()
    if key in keys:
        keys[key]["active"] = False
        try:
            KEYS_FILE.write_text(json.dumps(keys, indent=2))
        except Exception:
            pass
        return True
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):

    SKIP_PATHS = {"/", "/ping", "/docs", "/redoc", "/openapi.json", "/widget", "/widget.js", "/dashboard"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.SKIP_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        api_key = request.headers.get("x-api-key") or request.query.get("api_key")

        if not api_key:
            return await call_next(request)

        keys = _load_keys()
        entry = keys.get(api_key)

        if not entry:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not entry.get("active", True):
            raise HTTPException(status_code=403, detail="API key has been revoked")

        plan = entry.get("plan", "free")
        plan_config = PLANS.get(plan, PLANS["free"])

        today = time.strftime("%Y-%m-%d")
        usage = _load_usage()
        day_usage = usage.get(api_key, {}).get(today, {"count": 0, "first_request": 0})

        if plan_config["requests_per_day"] > 0 and day_usage["count"] >= plan_config["requests_per_day"]:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit reached ({plan_config['requests_per_day']} requests). Upgrade to Pro.",
            )

        now = int(time.time())
        if plan_config["rate_limit_per_min"] > 0 and day_usage["first_request"] > 0:
            if now - day_usage["first_request"] < 60 and day_usage["count"] >= plan_config["rate_limit_per_min"]:
                raise HTTPException(status_code=429, detail="Rate limit: 10 requests per minute on Free plan.")

        if api_key not in usage:
            usage[api_key] = {}
        if today not in usage[api_key]:
            usage[api_key][today] = {"count": 0, "first_request": now}
        usage[api_key][today]["count"] += 1
        if usage[api_key][today]["count"] == 1:
            usage[api_key][today]["first_request"] = now

        if len(usage[api_key]) > 30:
            sorted_days = sorted(usage[api_key].keys())
            for old_day in sorted_days[:-30]:
                del usage[api_key][old_day]

        _save_usage(usage)

        request.state.api_key = api_key
        request.state.plan = plan

        return await call_next(request)
