from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from app.config import settings
from app.api.v1 import market, defi, whales, health, alerts, news, admin, security, signals, forex, admin_publish


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
        description=(
            "# ChainSight API — Unified Crypto Intelligence\n\n"
            "**30+ endpoints** for real-time crypto prices, on-chain whale tracking, DeFi analytics, "
            "security checks (honeypot), forex/stocks, and alpha signals.\n\n"
            "---\n\n"
            "## Quick Start\n"
            "1. **Free tier** — `/v1/market/top`, `/v1/market/coin/{id}`, `/v1/defi/protocols`, `/v1/whales/eth`\n"
            "2. **Pro tier** — `/v1/security/honeypot/{address}`, `/v1/signals/momentum`, `/v1/signals/whale-accumulation`\n\n"
            "---\n\n"
            "## Endpoints by Category\n"
            "| Category | Endpoints | Auth |\n"
            "| --- | --- | --- |\n"
            "| Market | `/v1/market/top`, `/coin/{id}`, `/coins`, `/compare`, `/trending`, `/global`, `/history`, `/correlation`, `/fear-greed`, `/news` | Free |\n"
            "| DeFi | `/v1/defi/protocols`, `/yields`, `/stablecoins` | Free |\n"
            "| Whales | `/v1/whales/eth`, `/chain/{chain}`, `/gas`, `/chains` | Free |\n"
            "| Forex | `/v1/forex/rates`, `/pairs`, `/history`, `/overview`, `/search`, `/major` | Free |\n"
            "| Security | `/v1/security/honeypot/{address}`, `/token/{address}`, `/batch-check` | Pro |\n"
            "| Signals | `/v1/signals/momentum`, `/whale-accumulation`, `/volume-anomaly` | Pro |\n"
            "| Alerts | `/v1/alerts/webhook` (CRUD) | Free |\n\n"
            "---\n\n"
            "## Rate Limits\n"
            "- Free: 60 req/min\n"
            "- Pro: 600 req/min\n\n"
            "## Pricing\n"
            "- **Free** — Market, DeFi, Whales, Forex, News\n"
            "- **Pro $9.99/mo** — + Security, Alpha Signals, White-label widgets\n\n"
            "---\n\n"
            "[RapidAPI](https://rapidapi.com/storbaz/api/chainsight) · "
            "[Telegram Bot](https://t.me/CryptoInsightAPI_bot) · "
            "[GitHub](https://github.com/storbaz/chainsight-api)"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Health", "description": "API health checks"},
            {"name": "Market", "description": "Real-time prices, trending coins, global stats, fear & greed index"},
            {"name": "DeFi", "description": "DeFi protocols, yields, stablecoins"},
            {"name": "Whales", "description": "On-chain whale transaction tracking across 9 chains"},
            {"name": "Forex", "description": "Forex rates, stocks, commodities via ECB + Yahoo Finance"},
            {"name": "Security", "description": "Honeypot detection, token audit, batch safety checks (Pro)"},
            {"name": "Signals", "description": "Alpha signals: momentum (RSI/MACD/Bollinger/Stochastic/VWAP), whale accumulation, volume anomalies (Pro)"},
            {"name": "Alerts", "description": "Webhook alerts for whale movements"},
            {"name": "News", "description": "Aggregated crypto news from top sources"},
            {"name": "Admin", "description": "Internal admin endpoints"},
            {"name": "Root", "description": "API root with endpoint index"},
            {"name": "Widget", "description": "Embeddable crypto widgets for websites"},
            {"name": "Dashboard", "description": "Live analytics dashboard"},
        ],
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
    app.include_router(admin.router, prefix="/v1")
    app.include_router(security.router, prefix="/v1")
    app.include_router(signals.router, prefix="/v1")
    app.include_router(forex.router, prefix="/v1")
    app.include_router(admin_publish.router, prefix="/v1")

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
                "honeypot_check": "/v1/security/honeypot/{address}?chain=ethereum",
                "token_audit": "/v1/security/token/{address}?chain=ethereum",
                "whale_accumulation": "/v1/signals/whale-accumulation",
                "volume_anomaly": "/v1/signals/volume-anomaly",
                "momentum": "/v1/signals/momentum?coin_id=bitcoin",
                "forex_rates": "/v1/forex/rates?base=EUR&symbols=USD,GBP,JPY",
                "forex_pairs": "/v1/forex/pairs",
                "forex_overview": "/v1/forex/overview",
                "forex_history": "/v1/forex/history?symbol=EUR/USD&range=1mo",
            },
        }

    @app.get("/widget", response_class=HTMLResponse, tags=["Widget"])
    async def widget():
        return """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChainSight Widgets - Embed Crypto Data</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#0a0a1a;color:white;padding:20px}
h1{text-align:center;margin-bottom:8px;font-size:22px}
.sub{text-align:center;color:#888;font-size:13px;margin-bottom:24px}
section{margin-bottom:32px}
section h2{font-size:14px;color:#00d4aa;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}
.code-box{background:#1a1a3e;border-radius:8px;padding:12px;font-family:monospace;font-size:12px;color:#00d4aa;word-break:break-all;margin-bottom:12px}
.preview{border:1px dashed #333;border-radius:12px;padding:16px;margin-top:8px}
</style>
</head>
<body>
<h1>ChainSight Widgets</h1>
<p class="sub">Embeddable crypto widgets for any website - Free & Premium</p>

<section>
<h2>Free Widgets</h2>
<p style="color:#888;font-size:12px;margin-bottom:12px">Free widgets include a "Powered by ChainSight" link. Remove it with a Pro API key.</p>
</section>

<section>
<h2>1. Card Widget (Free)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="card" data-coins="5" data-theme="dark" data-accent="#00d4aa" data-label="ChainSight"&gt;&lt;/script&gt;</div>
<div class="preview"><script src="/widget.js" data-type="card" data-coins="5" data-theme="dark" data-accent="#00d4aa" data-label="ChainSight"></script></div>
</section>

<section>
<h2>2. Ticker Widget (Free)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="ticker" data-coins="5" data-theme="dark" data-accent="#00d4aa" data-label="Crypto"&gt;&lt;/script&gt;</div>
<div class="preview"><script src="/widget.js" data-type="ticker" data-coins="5" data-theme="dark" data-accent="#00d4aa" data-label="Crypto"></script></div>
</section>

<section>
<h2>3. Portfolio Widget (Free)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="portfolio" data-theme="dark" data-accent="#00d4aa" data-label="My Portfolio"&gt;&lt;/script&gt;</div>
<div class="preview"><script src="/widget.js" data-type="portfolio" data-theme="dark" data-accent="#00d4aa" data-label="My Portfolio"></script></div>
</section>

<section>
<h2>4. Whale Alerts (Free)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="whale-alerts" data-theme="dark" data-accent="#ff9f43"&gt;&lt;/script&gt;</div>
<div class="preview"><script src="/widget.js" data-type="whale-alerts" data-theme="dark" data-accent="#ff9f43"></script></div>
</section>

<section style="margin-top:32px">
<h2 style="color:#ff9f43">Premium Widgets (Pro)</h2>
<p style="color:#888;font-size:12px;margin-bottom:12px">Premium widgets require a Pro API key via <code style="color:#00d4aa">data-api-key="cs_YOUR_KEY"</code>. No watermark, enhanced features.</p>
</section>

<section>
<h2>5. Live Alerts (Pro)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="alerts-live" data-api-key="cs_YOUR_KEY" data-theme="dark" data-accent="#ff9f43"&gt;&lt;/script&gt;</div>
<div class="preview"><div style="font-family:-apple-system,sans-serif;background:#0a0a1a;color:#fff;padding:20px;border-radius:12px;text-align:center;border:1px solid #2a2a4a"><div style="font-size:14px;font-weight:700;margin-bottom:8px">Premium Widget</div><div style="font-size:12px;color:#888">Requires Pro API key to preview</div></div></div>
</section>

<section>
<h2>6. Whale Tracker (Pro)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="whale-tracker" data-api-key="cs_YOUR_KEY" data-theme="dark" data-accent="#00d4aa"&gt;&lt;/script&gt;</div>
</section>

<section>
<h2>7. Advanced Portfolio (Pro)</h2>
<div class="code-box">&lt;script src="https://chainsight-api.onrender.com/widget.js" data-type="portfolio-advanced" data-api-key="cs_YOUR_KEY" data-theme="dark" data-accent="#00d4aa" data-label="Pro Portfolio"&gt;&lt;/script&gt;</div>
</section>

<section>
<h2>Attributes</h2>
<div style="background:#1a1a3e;border-radius:8px;padding:16px;font-size:13px;line-height:1.8">
<div><code style="color:#00d4aa">data-type</code> — card | ticker | portfolio | whale-alerts (Free) | alerts-live | whale-tracker | portfolio-advanced (Pro)</div>
<div><code style="color:#ff9f43">data-api-key</code> — Your ChainSight Pro API key (removes watermark, unlocks premium widgets)</div>
<div><code style="color:#00d4aa">data-theme</code> — dark | light</div>
<div><code style="color:#00d4aa">data-accent</code> — hex color (e.g. #00d4aa, #ff9f43)</div>
<div><code style="color:#00d4aa">data-label</code> — custom brand name</div>
<div><code style="color:#00d4aa">data-coins</code> — number of coins to show (card/ticker)</div>
<div><code style="color:#00d4aa">data-target</code> — DOM element ID to render into</div>
</div>
</section>

<section>
<h2>Pricing</h2>
<div style="display:flex;gap:12px;flex-wrap:wrap">
<div style="background:#1a1a3e;border-radius:8px;padding:16px;flex:1;min-width:200px;border:1px solid #2a2a4a">
<div style="color:#00d4aa;font-weight:700;font-size:14px">Free</div>
<div style="color:#888;font-size:12px;margin-top:4px">Card, Ticker, Portfolio, Whale Alerts</div>
<div style="color:#fff;font-size:11px;margin-top:4px">Watermark included | 100 API calls/day</div>
</div>
<div style="background:#1a1a3e;border-radius:8px;padding:16px;flex:1;min-width:200px;border:1px solid #00d4aa">
<div style="color:#00d4aa;font-weight:700;font-size:14px">Pro - $9.99/mo</div>
<div style="color:#888;font-size:12px;margin-top:4px">All widgets + no watermark + premium widgets</div>
<div style="color:#fff;font-size:11px;margin-top:4px">Honeypot check | Alpha signals | 10,000 API calls/day</div>
</div>
</div>
</section>

<div style="text-align:center;padding:20px;font-size:11px;color:#444">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" style="color:#00d4aa">ChainSight API</a></div>
</body>
</html>"""

    @app.get("/widget.js", tags=["Widget"])
    async def widget_js():
        js = r"""
(function(){
  var s=document.currentScript;
  var type=s.getAttribute("data-type")||"card";
  var coins=parseInt(s.getAttribute("data-coins"))||5;
  var theme=s.getAttribute("data-theme")||"dark";
  var accent=s.getAttribute("data-accent")||"#00d4aa";
  var label=s.getAttribute("data-label")||"ChainSight";
  var apiKey=s.getAttribute("data-api-key")||"";
  var API="https://chainsight-api.onrender.com";
  var host=s.getAttribute("data-target")?document.getElementById(s.getAttribute("data-target")):null;
  if(!host){host=document.createElement("div");s.parentNode.insertBefore(host,s.nextSibling);}

  var bg=theme==="light"?"#ffffff":"#0a0a1a";
  var card=theme==="light"?"#f0f0f5":"#1a1a3e";
  var txt=theme==="light"?"#333":"#fff";
  var sub=theme==="light"?"#666":"#888";
  var border=theme==="light"?"#e0e0e0":"#2a2a4a";

  var isPro=apiKey&&apiKey.indexOf("cs_")===0;
  var ftHtml=isPro?"":'<div style="text-align:center;padding:6px 0 0;font-size:9px;color:'+sub+';letter-spacing:.5px">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank" style="color:'+accent+';text-decoration:none">ChainSight</a> | Free Plan</div>';

  var premiumOnly=['white-label','portfolio-advanced','alerts-live','whale-tracker'];
  if(premiumOnly.indexOf(type)!==-1&&!isPro){
    host.innerHTML='<div style="font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:20px;border-radius:12px;border:1px solid '+border+';text-align:center;max-width:400px"><div style="font-size:14px;font-weight:700;margin-bottom:8px">Premium Widget</div><div style="font-size:12px;color:'+sub+';margin-bottom:12px">This widget requires a ChainSight Pro API key.</div><a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank" style="display:inline-block;padding:8px 20px;background:'+accent+';color:#000;border-radius:6px;font-size:12px;font-weight:700;text-decoration:none">Get Pro API Key</a></div>';
    return;
  }

  if(type==="ticker"){
    host.innerHTML='<style>#cs-tk{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:8px 16px;border-radius:6px;overflow:hidden;white-space:nowrap;font-size:13px;display:flex;gap:24px;align-items:center;border:1px solid '+border+'}#cs-tk .cs{font-weight:700}#cs-tk .cv{margin-left:4px}#cs-tk .cc{font-size:11px;margin-left:4px}#cs-tk .up{color:'+accent+'}#cs-tk .dn{color:#ff4757}#cs-tk .lb{font-size:10px;color:'+sub+';margin-right:8px;text-transform:uppercase;letter-spacing:1px}</style><div id="cs-tk"><span class="lb">'+label+'</span></div>';
    fetch(API+"/v1/market/top?limit="+coins).then(function(r){return r.json()}).then(function(d){
      document.getElementById("cs-tk").innerHTML='<span class="lb">'+label+'</span>'+d.map(function(c){var ch=c.price_change_percentage_24h||0;return'<span><span class="cs">'+c.symbol.toUpperCase()+'</span><span class="cv">$'+c.current_price.toLocaleString()+'</span><span class="cc '+(ch>=0?"up":"dn")+'">'+(ch>=0?"+":"")+ch.toFixed(1)+'%</span></span>'}).join('<span style="color:'+border+'">|</span>')+ftHtml;
    });
  }

  else if(type==="portfolio"||type==="portfolio-advanced"){
    var saved=[];
    try{saved=JSON.parse(localStorage.getItem("cs-portfolio")||"[]");}catch(e){}
    var inputHtml='<div style="display:flex;gap:6px;margin-bottom:10px"><input id="cs-pi" placeholder="coin id (bitcoin)" style="flex:1;padding:6px;border-radius:4px;border:1px solid '+border+';background:'+card+';color:'+txt+';font-size:12px"><input id="cs-pq" type="number" placeholder="qty" value="1" style="width:60px;padding:6px;border-radius:4px;border:1px solid '+border+';background:'+card+';color:'+txt+';font-size:12px"><button id="cs-pa" style="padding:6px 10px;border-radius:4px;border:none;background:'+accent+';color:#000;font-weight:700;cursor:pointer;font-size:12px">+</button></div>';
    var histHtml=type==="portfolio-advanced"?'<div id="cs-ph" style="margin-top:10px"></div>':'';
    host.innerHTML='<style>#cs-pf{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:16px;border-radius:12px;max-width:400px;border:1px solid '+border+'}#cs-pf .hd{font-size:14px;font-weight:700;margin-bottom:10px}#cs-pf .rw{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid '+border+';font-size:12px}#cs-pf .rw:last-child{border:none}#cs-pf .tp{text-align:right;font-weight:700;margin-top:10px;font-size:14px}#cs-pf .ft{text-align:center;font-size:10px;color:'+sub+';margin-top:8px}#cs-pf .ft a{color:'+accent+';text-decoration:none}#cs-pf .pl{color:#ff4757}#cs-pf .pm{color:'+accent+'}</style><div id="cs-pf"><div class="hd">'+label+' Portfolio</div>'+inputHtml+'<div id="cs-pl"></div><div class="tp" id="cs-pt"></div>'+histHtml+'<div class="ft">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight</a></div></div>';
    document.getElementById("cs-pa").onclick=function(){
      var id=document.getElementById("cs-pi").value.trim();
      var qty=parseFloat(document.getElementById("cs-pq").value)||1;
      if(!id)return;
      saved.push({id:id,qty:qty});
      localStorage.setItem("cs-portfolio",JSON.stringify(saved));
      document.getElementById("cs-pi").value="";
      loadPortfolio();
    };
    loadPortfolio();
    function loadPortfolio(){
      if(!saved.length){document.getElementById("cs-pl").innerHTML='<div style="color:'+sub+';font-size:12px;text-align:center;padding:10px">Add coins above</div>';document.getElementById("cs-pt").textContent="";return;}
      var ids=saved.map(function(x){return x.id}).join(",");
      fetch(API+"/v1/market/coins?ids="+ids).then(function(r){return r.json()}).then(function(d){
        var total=0;var totalCost=0;
        var rows=saved.map(function(s,i){var coin=d.find(function(c){return c.id===s.id});if(!coin)return"";var val=(coin.current_price||0)*s.qty;var ch=coin.price_change_percentage_24h||0;total+=val;var cls=ch>=0?"pm":"pl";return'<div class="rw"><span>'+coin.symbol.toUpperCase()+' '+s.qty+' <span class="'+cls+'" style="font-size:10px">('+(ch>=0?"+":"")+ch.toFixed(1)+'%)</span></span><span>$'+val.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+'</span></div>'}).join("");
        document.getElementById("cs-pl").innerHTML=rows;
        document.getElementById("cs-pt").textContent="Total: $"+total.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
      });
    }
  }

  else if(type==="whale-alerts"||type==="whale-tracker"){
    host.innerHTML='<style>#cs-wa{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:16px;border-radius:12px;max-width:400px;border:1px solid '+border+'}#cs-wa .hd{font-size:14px;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:6px}#cs-wa .dot{width:8px;height:8px;border-radius:50%;background:#ff4757;animation:cs-pulse 2s infinite}#cs-wa .rw{background:'+card+';border-radius:8px;padding:8px;margin-bottom:6px;font-size:12px}#cs-wa .rw .vl{color:'+accent+';font-weight:700}#cs-wa .rw .tm{color:'+sub+';font-size:10px;float:right}#cs-wa .rw .ad{color:'+sub+';font-size:10px;word-break:break-all}#cs-wa .rw .lb{font-size:10px;color:'+sub+'}#cs-wa .ft{text-align:center;font-size:10px;color:'+sub+';margin-top:8px}#cs-wa .ft a{color:'+accent+';text-decoration:none}@keyframes cs-pulse{0%,100%{opacity:1}50%{opacity:.3}}</style><div id="cs-wa"><div class="hd"><span class="dot"></span> Whale Alerts</div><div id="cs-wl"><div style="color:'+sub+'">Loading...</div></div><div class="ft">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight</a></div></div>';
    var minVal=type==="whale-tracker"?"500":"100";
    fetch(API+"/v1/whales/eth?min_value="+minVal+"&limit=5").then(function(r){return r.json()}).then(function(d){
      var filtered=d.filter(function(t){return t.hash});
      if(!filtered.length){document.getElementById("cs-wl").innerHTML='<div style="color:'+sub+'">No recent whales</div>';return;}
      document.getElementById("cs-wl").innerHTML=filtered.map(function(tx){
        var tm=tx.timestamp?new Date(parseInt(tx.timestamp)*1000).toLocaleTimeString():"";
        var lbl=tx.label?'<div class="lb">'+tx.label+'</div>':"";
        return'<div class="rw"><span class="tm">'+tm+'</span><div class="vl">'+tx.value+' ETH</div>'+lbl+'<div class="ad">'+(tx.from_address||"").slice(0,16)+'...</div></div>';
      }).join("");
    });
  }

  else if(type==="alerts-live"){
    host.innerHTML='<style>#cs-al{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:16px;border-radius:12px;max-width:400px;border:1px solid '+border+'}#cs-al .hd{font-size:14px;font-weight:700;margin-bottom:10px;display:flex;align-items:center;gap:6px}#cs-al .dot{width:8px;height:8px;border-radius:50%5;background:'+accent+';animation:cs-pulse 1.5s infinite}#cs-al .rw{background:'+card+';border-radius:8px;padding:8px;margin-bottom:6px;font-size:12px;border-left:3px solid '+accent+'}#cs-al .rw .vl{color:'+accent+';font-weight:700;font-size:14px}#cs-al .rw .rp{color:#ff4757;font-size:11px}#cs-al .rw .tm{color:'+sub+';font-size:10px;float:right}#cs-al .ft{text-align:center;font-size:10px;color:'+sub+';margin-top:8px}@keyframes cs-pulse{0%,100%{opacity:1}50%{opacity:.3}}</style><div id="cs-al"><div class="hd"><span class="dot"></span> Live Whale Tracker</div><div id="cs-alr"><div style="color:'+sub+'">Loading...</div></div><div class="ft">Auto-refreshes every 60s | ChainSight Pro</div></div>';
    function loadAlerts(){
      fetch(API+"/v1/whales/eth?min_value=50&limit=10").then(function(r){return r.json()}).then(function(d){
        var f=d.filter(function(t){return t.hash}).slice(0,5);
        if(!f.length){document.getElementById("cs-alr").innerHTML='<div style="color:'+sub+'">No recent activity</div>';return;}
        document.getElementById("cs-alr").innerHTML=f.map(function(tx){
          var tm=tx.timestamp?new Date(parseInt(tx.timestamp)*1000).toLocaleTimeString():"";
          var val=tx.value||0;
          return'<div class="rw"><span class="tm">'+tm+'</span><div class="vl">'+val+' ETH</div>'+(tx.label?'<div class="rp">'+tx.label+'</div>':'')+'</div>';
        }).join("");
      });
    }
    loadAlerts();setInterval(loadAlerts,60000);
  }

  else{
    host.innerHTML='<style>#cs-w{font-family:-apple-system,sans-serif;background:'+bg+';color:'+txt+';padding:16px;border-radius:12px;max-width:400px;margin:0 auto;border:1px solid '+border+'}#cs-w .h{text-align:center;margin-bottom:12px}#cs-w .h h3{font-size:16px;margin:0}#cs-w .h p{font-size:11px;color:'+sub+'}#cs-w .fg{background:'+card+';border-radius:10px;padding:16px;text-align:center;margin-bottom:12px}#cs-w .fg .v{font-size:36px;font-weight:700}#cs-w .fg .l{font-size:12px;color:'+sub+'}#cs-w .cl{display:grid;gap:8px}#cs-w .c{background:'+card+';border-radius:8px;padding:10px;display:flex;justify-content:space-between;align-items:center}#cs-w .ci{display:flex;align-items:center;gap:8px}#cs-w .cs{font-weight:700;font-size:13px}#cs-w .cn{font-size:11px;color:'+sub+'}#cs-w .cp{text-align:right}#cs-w .cv{font-weight:700;font-size:13px}#cs-w .cc{font-size:11px}#cs-w .up{color:'+accent+'}#cs-w .dn{color:#ff4757}#cs-w .ft{text-align:center;margin-top:12px;font-size:10px;color:'+sub+'}#cs-w .ft a{color:'+accent+';text-decoration:none}</style><div id="cs-w"><div class="h"><h3>'+label+'</h3><p>Real-time crypto data</p></div><div class="fg" id="cs-fg"><div class="v">--</div><div class="l">Loading...</div></div><div class="cl" id="cs-coins"></div><div class="ft">Powered by <a href="https://rapidapi.com/storbaz/api/chainsight" target="_blank">ChainSight</a></div></div>';
    async function load(){try{
      var t=await fetch(API+"/v1/market/top?limit="+coins);
      var r=await fetch(API+"/v1/market/fear-greed");
      var td=await t.json(),rd=await r.json();
      document.getElementById("cs-fg").innerHTML='<div class="v">'+rd.value+'</div><div class="l">'+rd.classification+'</div>';
      document.getElementById("cs-coins").innerHTML=td.map(function(c){var ch=c.price_change_percentage_24h||0;return'<div class="c"><div class="ci"><span class="cs">'+c.symbol.toUpperCase()+'</span><span class="cn">'+c.name+'</span></div><div class="cp"><div class="cv">$'+c.current_price.toLocaleString()+'</div><div class="cc '+(ch>=0?"up":"dn")+'">'+(ch>=0?"+":"")+ch.toFixed(1)+'%</div></div></div>'}).join("");
    }catch(e){}}
    load();setInterval(load,60000);
  }
})();"""
        return Response(content=js, media_type="application/javascript")

    @app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
    async def dashboard():
        from pathlib import Path
        html = (Path(__file__).parent / "pages" / "dashboard.html").read_text()
        return HTMLResponse(content=html)

    return app


app = create_app()
