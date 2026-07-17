"""ChainSight Telegram Bot — Webhook mode for free hosting."""

import os
import httpx
from difflib import get_close_matches
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

CHAINSIGHT_BASE = os.environ.get("CHAINSIGHT_BASE_URL", "https://chainsight-api.onrender.com")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
COMMON_COINS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana",
    "ripple", "usd-coin", "steth", "dogecoin", "cardano",
    "avalanche-2", "polkadot", "chainlink", "tron", "litecoin",
    "uniswap", "stellar", "cosmos", "monero", "filecoin",
]

application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
api = FastAPI()
client = httpx.AsyncClient(timeout=10)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *ChainSight Bot*\n\n"
        "*Market:*\n"
        "/price <coin> — Get coin price\n"
        "/top — Top 10 coins\n"
        "/feargreed — Fear & Greed Index\n"
        "/search <query> — Search coins\n\n"
        "*DeFi & Security:*\n"
        "/defi — Top DeFi protocols\n"
        "/gas — Gas prices (all chains)\n"
        "/honeypot <address> — Check token safety\n\n"
        "*Forex & Stocks:*\n"
        "/forex <pair> — Forex rate (EUR/USD)\n"
        "/stocks <symbol> — Stock price (AAPL)\n"
        "/overview — Full market overview\n\n"
        "*Whales:*\n"
        "/whales <chain> — Whale txs (eth/btc/bsc/sol)\n\n"
        "*News:*\n"
        "/news — Latest crypto news",
        parse_mode="Markdown",
    )


async def _get(path: str, params: dict = None) -> dict | None:
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}{path}", params=params or {})
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /price bitcoin\n\n"
            "Popular: bitcoin, ethereum, solana, dogecoin, cardano, ripple"
        )
        return
    coin_id = context.args[0].lower().strip()
    data = await _get(f"/v1/market/coin/{coin_id}")
    if not data:
        suggestions = get_close_matches(coin_id, COMMON_COINS, n=3, cutoff=0.4)
        sug = f"\n\nDid you mean: {', '.join(suggestions)}?" if suggestions else f"\n\nTry: /search {coin_id}"
        await update.message.reply_text(f"❌ Coin '{coin_id}' not found.{sug}")
        return
    if "error" in data:
        await update.message.reply_text("⏳ Rate limited. Try again in a few seconds.")
        return
    await update.message.reply_text(
        f"💰 *{data['name']}* ({data['symbol'].upper()})\n\n"
        f"Price: ${data['current_price']:,.2f}\n"
        f"24h: {data['price_change_percentage_24h']:.2f}%\n"
        f"7d: {data.get('price_change_percentage_7d', 0) or 0:.2f}%\n"
        f"Market Cap: ${data['market_cap']:,.0f}\n"
        f"Rank: #{data['market_cap_rank']}",
        parse_mode="Markdown",
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/top", {"limit": 10})
    if not data:
        await update.message.reply_text("⏳ Data loading. Try again in 30s.")
        return
    lines = ["📊 *Top 10 Cryptocurrencies*\n"]
    for i, coin in enumerate(data, 1):
        change = coin.get("price_change_percentage_24h", 0) or 0
        emoji = "🟢" if change >= 0 else "🔴"
        lines.append(f"{i}. *{coin['name']}* — ${coin['current_price']:,.2f} {emoji} {change:.1f}%")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def feargreed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/fear-greed")
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    value = data["value"]
    cls = data["classification"]
    emoji = "😱" if value <= 25 else "😨" if value <= 45 else "😐" if value <= 55 else "😊" if value <= 75 else "🤑"
    await update.message.reply_text(
        f"{emoji} *Fear & Greed Index*\n\nValue: *{value}*/100\nClassification: *{cls}*",
        parse_mode="Markdown",
    )


async def defi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/defi/protocols", {"limit": 5})
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    lines = ["💰 *Top DeFi Protocols*\n"]
    for i, p in enumerate(data, 1):
        tvl = p.get("tvl", 0) or 0
        lines.append(f"{i}. *{p['name']}* — ${tvl/1e9:.2f}B TVL")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/whales/gas")
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    await update.message.reply_text(
        f"⛽ *Ethereum Gas*\n\n"
        f"Low: {data['low']:.1f} Gwei\n"
        f"Average: {data['average']:.1f} Gwei\n"
        f"Fast: {data['fast']:.1f} Gwei",
        parse_mode="Markdown",
    )


async def gas_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/whales/gas")
    chains_data = await _get("/v1/whales/chains")
    if not chains_data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    lines = ["⛽ *Gas Prices — All Chains*\n"]
    for chain in chains_data.get("chains", []):
        g = await _get("/v1/whales/gas", {"chain": chain["id"]})
        if g and "low" in g:
            lines.append(f"*{chain['name']}*: {g['low']:.1f} / {g['average']:.1f} / {g['fast']:.1f} {g.get('unit', 'gwei')}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search bitcoin")
        return
    query = " ".join(context.args)
    data = await _get("/v1/market/search", {"query": query})
    if not data:
        await update.message.reply_text(f"No results for '{query}'.")
        return
    lines = [f"🔍 *Results for '{query}'*\n"]
    for c in data[:5]:
        rank = c.get("market_cap_rank", "?")
        lines.append(f"• *{c['name']}* ({c['symbol'].upper()}) — Rank #{rank}")
    lines.append("\n💡 Use /price <id> for details")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def honeypot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /honeypot 0x...")
        return
    address = context.args[0].strip()
    data = await _get(f"/v1/security/honeypot/{address}")
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return
    is_hp = data.get("is_honeypot", False)
    risk = data.get("risk_level", "unknown")
    emoji = "🚨" if is_hp else "✅"
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
    lines = [
        f"{emoji} *Honeypot Check*\n",
        f"Address: `{address[:10]}...{address[-6:]}`",
        f"Honeypot: *{'YES' if is_hp else 'NO'}*",
        f"Risk: {risk_emoji} *{risk.upper()}*",
    ]
    if data.get("buy_tax") is not None:
        lines.append(f"Buy Tax: {data['buy_tax']}%")
    if data.get("sell_tax") is not None:
        lines.append(f"Sell Tax: {data['sell_tax']}%")
    if data.get("owner_can_sell"):
        lines.append("⚠️ Owner can sell")
    if data.get("hidden_owner"):
        lines.append("⚠️ Hidden owner")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "EUR/USD"
    if context.args:
        symbol = " ".join(context.args).upper()
    data = await _get("/v1/forex/rates", {"base": symbol.split("/")[0] if "/" in symbol else "EUR"})
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    rates = data.get("rates", {})
    date = data.get("date", "")
    lines = [f"💱 *Forex Rates* ({date})\n"]
    for cur, rate in rates.items():
        lines.append(f"*{data['base']}/{cur}*: {rate}")
    lines.append(f"\n💡 Try: /forex EUR/GBP, /forex USD/JPY")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /stocks AAPL\n\n"
            "Popular: AAPL, TSLA, NVDA, MSFT, GOOGL, SPY, QQQ"
        )
        return
    symbol = context.args[0].upper().strip()
    data = await _get("/v1/forex/history", {"symbol": symbol, "range": "5d", "interval": "1d"})
    if not data or "error" in data:
        await update.message.reply_text(f"❌ Could not get data for {symbol}")
        return
    summary = data.get("summary", {})
    current = summary.get("current", 0)
    high = summary.get("high", 0)
    low = summary.get("low", 0)
    change = summary.get("change_pct", 0)
    emoji = "🟢" if change >= 0 else "🔴"
    await update.message.reply_text(
        f"📈 *{symbol}*\n\n"
        f"Price: ${current:,.2f}\n"
        f"5d Change: {emoji} {change:+.2f}%\n"
        f"5d High: ${high:,.2f}\n"
        f"5d Low: ${low:,.2f}",
        parse_mode="Markdown",
    )


async def overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/forex/overview")
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    forex_pairs = data.get("forex", [])[:5]
    stocks_list = data.get("stocks", [])[:5]
    commodities = data.get("commodities", [])[:3]
    lines = ["📊 *Market Overview*\n"]
    if forex_pairs:
        lines.append("*Forex:*")
        for p in forex_pairs:
            ch = p.get("change_pct", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            lines.append(f"  {p['symbol']}: {p.get('rate', 0):.4f} {emoji} {ch:+.2f}%")
    if stocks_list:
        lines.append("\n*Stocks:*")
        for s in stocks_list:
            ch = s.get("change_pct", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            lines.append(f"  {s['symbol']}: ${s.get('price', 0):,.2f} {emoji} {ch:+.2f}%")
    if commodities:
        lines.append("\n*Commodities:*")
        for c in commodities:
            ch = c.get("change_pct", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            lines.append(f"  {c['symbol']}: ${c.get('price', 0):,.2f} {emoji} {ch:+.2f}%")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chain = context.args[0].lower() if context.args else "ethereum"
    data = await _get(f"/v1/whales/chain/{chain}", {"min_value": 100, "limit": 5})
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    valid = [t for t in data if "hash" in t]
    if not valid:
        msg = data[0].get("message", "No whale txs found") if data else "No data"
        await update.message.reply_text(f"🐋 *{chain.upper()} Whales*\n\n{msg}", parse_mode="Markdown")
        return
    lines = [f"🐋 *{chain.upper()} Whale Transactions*\n"]
    for tx in valid[:5]:
        val = tx.get("value", 0)
        sym = tx.get("token_symbol", "?")
        addr = tx.get("from_address", "?")
        short_addr = f"{addr[:8]}...{addr[-4:]}" if len(addr) > 12 else addr
        lines.append(f"*{val} {sym}* — {short_addr}")
    lines.append(f"\n💡 Chains: eth, btc, bsc, sol, polygon, arbitrum, base, optimism, avalanche")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/news", {"limit": 5})
    if not data:
        await update.message.reply_text("❌ Error. Try again.")
        return
    articles = data.get("articles", [])
    if not articles:
        await update.message.reply_text("📰 No news available right now.")
        return
    lines = ["📰 *Latest Crypto News*\n"]
    for a in articles[:5]:
        title = a.get("title", "")[:80]
        source = a.get("source", "")
        lines.append(f"• [{title}]({a.get('url', '#')})")
        lines.append(f"  _{source}_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)


application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", start))
application.add_handler(CommandHandler("price", price))
application.add_handler(CommandHandler("top", top))
application.add_handler(CommandHandler("feargreed", feargreed))
application.add_handler(CommandHandler("defi", defi))
application.add_handler(CommandHandler("gas", gas))
application.add_handler(CommandHandler("gasall", gas_all))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("honeypot", honeypot))
application.add_handler(CommandHandler("forex", forex))
application.add_handler(CommandHandler("stocks", stocks))
application.add_handler(CommandHandler("overview", overview))
application.add_handler(CommandHandler("whales", whales))
application.add_handler(CommandHandler("news", news))


@api.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url="https://crypto-insight-bot.onrender.com/webhook")
    print("Bot started with webhook")


@api.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


@api.get("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "running", "bot": "ChainSightBot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
