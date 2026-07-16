from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JavaScriptResponse
from app.config import settings
from app.api.v1 import market, defi, whales, health, alerts, news


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

    async def whale_monitor():
        from app.services.whale_service import whale_service
        from app.services.alert_service import alert_service
        await asyncio.sleep(30)
        while True:
            try:
                txs = await whale_service.get_eth_large_transactions(min_value_eth=50)
                real_txs = [t for t in txs if "hash" in t]
                if real_txs:
                    await alert_service.check_and_trigger(real_txs)
            except Exception:
                pass
            await asyncio.sleep(300)

    asyncio.create_task(keep_alive())
    asyncio.create_task(whale_monitor())
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
    app.include_router(alerts.router, prefix="/v1")
    app.include_router(news.router, prefix="/v1")

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
                "market_top": "/v1/market/top",
                "coin_detail": "/v1/market/coin/{coin_id}",
                "bulk_prices": "/v1/market/coins?ids=bitcoin,ethereum",
                "compare": "/v1/market/compare?coin1=bitcoin&coin2=ethereum",
                "trending": "/v1/market/trending",
                "global": "/v1/market/global",
                "price_history": "/v1/market/history?coin_id=bitcoin&days=30",
                "correlation": "/v1/market/correlation?ids=bitcoin,ethereum,s&p500",
                "fear_greed": "/v1/market/fear-greed",
                "defi_protocols": "/v1/defi/protocols",
                "defi_yields": "/v1/defi/yields",
                "stablecoins": "/v1/defi/stablecoins",
                "whale_txs": "/v1/whales/eth",
                "gas": "/v1/whales/gas",
                "webhook_alerts": "/v1/alerts/webhook",
                "news": "/v1/market/news",
            },
        }

    @app.get("/widget", response_class=HTMLResponse, tags=["Widget"])
    async def widget():
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChainSight Widget Preview</title>
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
.code-box{background:#1a1a3e;border-radius:8px;padding:16px;margin:20px auto;max-width:600px;font-family:monospace;font-size:13px;color:#00d4aa;word-break:break-all}
h3{text-align:center;margin:30px 0 10px;color:#888}
</style>
</head>
<body>
<h2 style="text-align:center">ChainSight Widget Preview</h2>
<p style="text-align:center;color:#888;margin-bottom:20px">Embed this on your site:</p>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-coins="5" data-theme="dark"&gt;&lt;/script&gt;</div>
<div id="chainsight-widget"></div>
<div class="footer">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight API</a></div>
<script src="/widget.js" data-coins="5" data-theme="dark"></script>
</body>
</html>"""

    @app.get("/widget.js", response_class=JavaScriptResponse, tags=["Widget"])
    async def widget_js():
        js = """
(function(){
  var s=document.currentScript;
  var coins=s.getAttribute("data-coins")||5;
  var theme=s.getAttribute("data-theme")||"dark";
  var API="https://chainsight-api.onrender.com";
  var host=document.getElementById("chainsight-widget");
  if(!host){host=document.createElement("div");host.id="chainsight-widget";s.parentNode.insertBefore(host,s.nextSibling);}
  var bg=theme==="light"?"#ffffff":"#0a0a1a";
  var card=theme==="light"?"#f0f0f5":"#1a1a3e";
  var txt=theme==="light"?"#333":"#fff";
  var sub=theme==="light"?"#666":"#888";
  host.innerHTML='<style>#cs-w{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:16px;border-radius:12px;max-width:400px;margin:0 auto}#cs-w .h{text-align:center;margin-bottom:12px}#cs-w .h h3{font-size:16px;margin:0}#cs-w .h p{font-size:11px;color:'+sub+'}#cs-w .fg{background:'+card+';border-radius:10px;padding:16px;text-align:center;margin-bottom:12px}#cs-w .fg .v{font-size:36px;font-weight:700}#cs-w .fg .l{font-size:12px;color:'+sub+'}#cs-w .cl{display:grid;gap:8px}#cs-w .c{background:'+card+';border-radius:8px;padding:10px;display:flex;justify-content:space-between;align-items:center}#cs-w .ci{display:flex;align-items:center;gap:8px}#cs-w .cs{font-weight:700;font-size:13px}#cs-w .cn{font-size:11px;color:'+sub+'}#cs-w .cp{text-align:right}#cs-w .cv{font-weight:700;font-size:13px}#cs-w .cc{font-size:11px}#cs-w .up{color:#00d4aa}#cs-w .dn{color:#ff4757}#cs-w .ft{text-align:center;margin-top:12px;font-size:10px;color:#666}#cs-w .ft a{color:#00d4aa;text-decoration:none}</style><div id="cs-w"><div class="h"><h3>ChainSight</h3><p>Real-time crypto data</p></div><div class="fg" id="cs-fg"><div class="v">--</div><div class="l">Loading...</div></div><div class="cl" id="cs-coins"></div><div class="ft">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight</a></div></div>';
  async function load(){try{
    var t=await fetch(API+"/v1/market/top?limit="+coins);
    var r=await fetch(API+"/v1/market/fear-greed");
    var td=await t.json(),rd=await r.json();
    document.getElementById("cs-fg").innerHTML='<div class="v">'+rd.value+'</div><div class="l">'+rd.classification+'</div>';
    document.getElementById("cs-coins").innerHTML=td.map(function(c){var ch=c.price_change_percentage_24h||0;return'<div class="c"><div class="ci"><span class="cs">'+c.symbol.toUpperCase()+'</span><span class="cn">'+c.name+'</span></div><div class="cp"><div class="cv">$'+c.current_price.toLocaleString()+'</div><div class="cc '+(ch>=0?"up":"dn")+'">'+(ch>=0?"+":"")+ch.toFixed(1)+'%</div></div></div>'}).join("");
  }catch(e){}}
  load();setInterval(load,60000);
})();"""
        return JavaScriptResponse(content=js, media_type="application/javascript")

    return app


app = create_app()
