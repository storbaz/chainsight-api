from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.config import settings
from app.api.v1 import market, defi, whales, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import httpx

    async def keep_alive():
        while True:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.get("https://chainsight-api.onrender.com/ping")
            except Exception:
                pass
            await asyncio.sleep(480)

    asyncio.create_task(keep_alive())
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Unified Crypto Intelligence API — Prices, On-Chain Data, DeFi Analytics, and Sentiment in one place.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["Health"])
    app.include_router(market.router, prefix="/v1")
    app.include_router(defi.router, prefix="/v1")
    app.include_router(whales.router, prefix="/v1")

    @app.api_route("/ping", methods=["GET", "HEAD"])
    async def ping():
        return {"ping": "pong"}

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "widget": "/widget",
            "endpoints": {
                "market": "/v1/market/top",
                "coin": "/v1/market/coin/{coin_id}",
                "global": "/v1/market/global",
                "fear_greed": "/v1/market/fear-greed",
                "defi_protocols": "/v1/defi/protocols",
                "defi_yields": "/v1/defi/yields",
                "stablecoins": "/v1/defi/stablecoins",
                "whale_txs": "/v1/whales/eth",
                "gas": "/v1/whales/gas",
            },
        }

    @app.get("/widget", response_class=HTMLResponse, tags=["Widget"])
    async def widget():
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0a0a1a;color:white;padding:20px}
.widget{max-width:400px;margin:0 auto}
.header{text-align:center;margin-bottom:20px}
.header h2{font-size:18px}
.header p{font-size:12px;color:#888}
.fear-greed{background:#1a1a3e;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px}
.fear-greed .value{font-size:48px;font-weight:700}
.fear-greed .label{font-size:14px;color:#888}
.coins{display:grid;gap:10px}
.coin{background:#1a1a3e;border-radius:8px;padding:12px;display:flex;justify-content:space-between;align-items:center}
.coin-info{display:flex;align-items:center;gap:10px}
.coin-symbol{font-weight:700;font-size:14px}
.coin-name{font-size:12px;color:#888}
.coin-price{text-align:right}
.coin-value{font-weight:700}
.coin-change{font-size:12px}
.up{color:#00d4aa}.down{color:#ff4757}
.footer{text-align:center;margin-top:20px;font-size:11px;color:#666}
.footer a{color:#00d4aa;text-decoration:none}
</style>
</head>
<body>
<div class="widget">
<div class="header"><h2>🔍 ChainSight</h2><p>Real-time crypto data</p></div>
<div class="fear-greed" id="fg"><div class="value">--</div><div class="label">Loading...</div></div>
<div class="coins" id="coins"></div>
<div class="footer">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight API</a></div>
</div>
<script>
const API="https://chainsight-api.onrender.com";
async function load(){try{
const[t,r]=await Promise.all([fetch(API+"/v1/market/top?limit=5"),fetch(API+"/v1/market/fear-greed")]);
const top=await t.json(),fg=await r.json();
document.getElementById("fg").innerHTML=`<div class="value">${fg.value}</div><div class="label">${fg.classification}</div>`;
document.getElementById("coins").innerHTML=top.map(c=>{const ch=c.price_change_percentage_24h||0;return`<div class="coin"><div class="coin-info"><span class="coin-symbol">${c.symbol.toUpperCase()}</span><span class="coin-name">${c.name}</span></div><div class="coin-price"><div class="coin-value">$${c.current_price.toLocaleString()}</div><div class="coin-change ${ch>=0?"up":"down"}">${ch>=0?"+":""}${ch.toFixed(1)}%</div></div></div>`}).join("");
}catch(e){console.error(e)}}
load();setInterval(load,60000);
</script>
</body>
</html>"""

    return app


app = create_app()
