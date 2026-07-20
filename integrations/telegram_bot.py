"""ChainSight Telegram Bot — Webhook mode for free hosting."""

import os
import json
import asyncio
import httpx
from difflib import get_close_matches
from fastapi import FastAPI, Request
from telegram import Update, Bot, MenuButtonCommands
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

CHAINSIGHT_BASE = os.environ.get("CHAINSIGHT_BASE_URL", "https://chainsight-api.onrender.com")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALERTS_FILE = "/tmp/price_alerts.json"
COMMON_COINS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana",
    "ripple", "usd-coin", "steth", "dogecoin", "cardano",
    "avalanche-2", "polkadot", "chainlink", "tron", "litecoin",
    "uniswap", "stellar", "cosmos", "monero", "filecoin",
]
VALID_CHAINS = ["ethereum", "bitcoin", "bsc", "solana", "polygon", "arbitrum", "base", "optimism", "avalanche"]

application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
api = FastAPI()
client = httpx.AsyncClient(timeout=10)

# ---------- Alerts persistence ----------

def _load_alerts() -> dict:
    try:
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_alerts(data: dict):
    with open(ALERTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _add_alert(user_id: int, coin_id: str, direction: str, target_price: float) -> str:
    alerts = _load_alerts()
    uid = str(user_id)
    if uid not in alerts:
        alerts[uid] = []
    alert_id = len(alerts[uid]) + 1
    alerts[uid].append({
        "id": alert_id,
        "coin": coin_id,
        "direction": direction,
        "target": target_price,
        "triggered": False,
    })
    _save_alerts(alerts)
    return alert_id


def _remove_alert(user_id: int, alert_id: int) -> bool:
    alerts = _load_alerts()
    uid = str(user_id)
    if uid in alerts:
        alerts[uid] = [a for a in alerts[uid] if a.get("id") != alert_id]
        _save_alerts(alerts)
        return True
    return False


# ---------- Helpers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔍 <b>ChainSight Bot</b>\n\n"
        "<b>Market:</b>\n"
        "/price coin — Get coin price\n"
        "/top — Top 10 coins\n"
        "/feargreed — Fear & Greed Index\n"
        "/overview — Gold, forex, stocks & crypto\n"
        "/search query — Search coins\n\n"
        "<b>DeFi & Security:</b>\n"
        "/defi — Top DeFi protocols\n"
        "/gas — Gas prices (all chains)\n"
        "/honeypot address — Check token safety\n\n"
        "<b>Forex & Commodities:</b>\n"
        "/forex pair — Forex rate (EUR/USD)\n"
        "/stocks symbol — Stock price (AAPL)\n\n"
        "<b>Whales:</b>\n"
        "/whales chain — Whale txs (eth/btc/bsc/sol)\n\n"
        "<b>News:</b>\n"
        "/news — Latest crypto news\n\n"
        "<b>Price Alerts:</b>\n"
        "/alert coin above|below price — Set alert\n"
        "/alerts — List your alerts\n"
        "/cancel id — Remove alert"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    try:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonCommands(type="commands"),
        )
    except Exception:
        pass


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
        await update.message.reply_text(f"Coin '{coin_id}' not found.{sug}")
        return
    if "error" in data:
        await update.message.reply_text("Rate limited. Try again in a few seconds.")
        return
    change_7d = data.get("price_change_percentage_7d", 0) or 0
    await update.message.reply_text(
        f"💰 {data['name']} ({data['symbol'].upper()})\n\n"
        f"Price: ${data['current_price']:,.2f}\n"
        f"24h: {data['price_change_percentage_24h']:.2f}%\n"
        f"7d: {change_7d:.2f}%\n"
        f"Market Cap: ${data['market_cap']:,.0f}\n"
        f"Rank: #{data['market_cap_rank']}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/top", {"limit": 10})
    if not data:
        await update.message.reply_text("Data loading. Try again in 30s.")
        return
    lines = ["📊 <b>Top 10 Cryptocurrencies</b>\n"]
    for i, coin in enumerate(data, 1):
        change = coin.get("price_change_percentage_24h", 0) or 0
        emoji = "🟢" if change >= 0 else "🔴"
        lines.append(f"{i}. <b>{coin['name']}</b> — ${coin['current_price']:,.2f} {emoji} {change:.1f}%")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def feargreed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/fear-greed")
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    value = data["value"]
    cls = data["classification"]
    emoji = "😱" if value <= 25 else "😨" if value <= 45 else "😐" if value <= 55 else "😊" if value <= 75 else "🤑"
    await update.message.reply_text(
        f"{emoji} <b>Fear &amp; Greed Index</b>\n\nValue: <b>{value}</b>/100\nClassification: <b>{cls}</b>",
        parse_mode="HTML",
    )


async def defi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/defi/protocols", {"limit": 5})
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    lines = ["💰 <b>Top DeFi Protocols</b>\n"]
    for i, p in enumerate(data, 1):
        tvl = p.get("tvl", 0) or 0
        lines.append(f"{i}. <b>{p['name']}</b> — ${tvl/1e9:.2f}B TVL")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/whales/gas")
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    await update.message.reply_text(
        f"⛽ <b>Ethereum Gas</b>\n\n"
        f"Low: {data['low']:.1f} Gwei\n"
        f"Average: {data['average']:.1f} Gwei\n"
        f"Fast: {data['fast']:.1f} Gwei",
        parse_mode="HTML",
    )


async def gas_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chains_data = await _get("/v1/whales/chains")
    if not chains_data:
        await update.message.reply_text("Error. Try again.")
        return
    lines = ["⛽ <b>Gas Prices — All Chains</b>\n"]
    for chain in chains_data.get("chains", []):
        g = await _get("/v1/whales/gas", {"chain": chain["id"]})
        if g and "low" in g:
            lines.append(f"<b>{chain['name']}</b>: {g['low']:.1f} / {g['average']:.1f} / {g['fast']:.1f} {g.get('unit', 'gwei')}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search bitcoin")
        return
    query = " ".join(context.args)
    data = await _get("/v1/market/search", {"query": query})
    if not data:
        await update.message.reply_text(f"No results for '{query}'.")
        return
    lines = [f"🔍 <b>Results for '{query}'</b>\n"]
    for c in data[:5]:
        rank = c.get("market_cap_rank", "?")
        lines.append(f"• <b>{c['name']}</b> ({c['symbol'].upper()}) — Rank #{rank}")
    lines.append("\n💡 Use /price id for details")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def honeypot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /honeypot 0x...")
        return
    address = context.args[0].strip()
    if not address.startswith("0x") or len(address) < 10:
        await update.message.reply_text("Invalid address. Must start with 0x and be at least 10 chars.")
        return
    data = await _get(f"/v1/security/honeypot/{address}")
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    if "error" in data:
        await update.message.reply_text(f"❌ {data['error']}")
        return
    is_hp = data.get("is_honeypot", False)
    risk = data.get("risk_level", "unknown")
    emoji = "🚨" if is_hp else "✅"
    risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "⚪")
    lines = [
        f"{emoji} <b>Honeypot Check</b>\n",
        f"Address: <code>{address[:10]}...{address[-6:]}</code>",
        f"Honeypot: <b>{'YES' if is_hp else 'NO'}</b>",
        f"Risk: {risk_emoji} <b>{risk.upper()}</b>",
    ]
    if data.get("buy_tax") is not None:
        lines.append(f"Buy Tax: {data['buy_tax']}%")
    if data.get("sell_tax") is not None:
        lines.append(f"Sell Tax: {data['sell_tax']}%")
    if data.get("owner_can_sell"):
        lines.append("⚠️ Owner can sell")
    if data.get("hidden_owner"):
        lines.append("⚠️ Hidden owner")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = "EUR/USD"
    if context.args:
        symbol = " ".join(context.args).upper()
    data = await _get("/v1/forex/rates", {"base": symbol.split("/")[0] if "/" in symbol else "EUR"})
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    rates = data.get("rates", {})
    date = data.get("date", "")
    lines = [f"💱 <b>Forex Rates</b> ({date})\n"]
    for cur, rate in rates.items():
        lines.append(f"<b>{data['base']}/{cur}</b>: {rate}")
    lines.append(f"\n💡 Try: /forex EUR/GBP, /forex USD/JPY")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /stocks AAPL\n\n"
            "Popular: AAPL, TSLA, NVDA, MSFT, GOOGL, SPY, QQQ"
        )
        return
    symbol = context.args[0].upper().strip()
    if not symbol.isalpha():
        await update.message.reply_text("Invalid symbol. Use letters only (e.g. AAPL).")
        return
    data = await _get("/v1/forex/history", {"symbol": symbol, "range": "5d", "interval": "1d"})
    if not data or "error" in data:
        await update.message.reply_text(f"Could not get data for {symbol}")
        return
    summary = data.get("summary", {})
    current = summary.get("current", 0)
    high = summary.get("high", 0)
    low = summary.get("low", 0)
    change = summary.get("change_pct", 0)
    emoji = "🟢" if change >= 0 else "🔴"
    await update.message.reply_text(
        f"📈 <b>{symbol}</b>\n\n"
        f"Price: ${current:,.2f}\n"
        f"5d Change: {emoji} {change:+.2f}%\n"
        f"5d High: ${high:,.2f}\n"
        f"5d Low: ${low:,.2f}",
        parse_mode="HTML",
    )


async def overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/forex/overview")
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    forex_pairs = data.get("forex", [])[:5]
    stocks_list = data.get("stocks", [])[:5]
    commodities = data.get("commodities", [])[:4]
    lines = ["📊 <b>Market Overview</b>\n"]
    if commodities:
        lines.append("<b>Commodities:</b>")
        for c in commodities:
            price = c.get("price", 0) or 0
            ch = c.get("change_24h", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            name = c.get("name", c["symbol"])
            lines.append(f"  {name}: ${price:,.2f} {emoji} {ch:+.2f}%")
    if forex_pairs:
        lines.append("\n<b>Forex:</b>")
        for p in forex_pairs:
            price = p.get("price", 0) or 0
            ch = p.get("change_24h", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            lines.append(f"  {p['symbol']}: {price:.4f} {emoji} {ch:+.2f}%")
    if stocks_list:
        lines.append("\n<b>Stocks:</b>")
        for s in stocks_list:
            price = s.get("price", 0) or 0
            ch = s.get("change_24h", 0) or 0
            emoji = "🟢" if ch >= 0 else "🔴"
            lines.append(f"  {s['symbol']}: ${price:,.2f} {emoji} {ch:+.2f}%")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def whales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chain = context.args[0].lower() if context.args else "ethereum"
    if chain not in VALID_CHAINS:
        await update.message.reply_text(
            f"Invalid chain: '{chain}'\n\n"
            f"Valid chains: {', '.join(VALID_CHAINS)}"
        )
        return
    data = await _get(f"/v1/whales/chain/{chain}", {"min_value": 100, "limit": 5})
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    valid = [t for t in data if "hash" in t]
    if not valid:
        msg = data[0].get("message", "No whale txs found") if data else "No data"
        await update.message.reply_text(f"🐋 <b>{chain.upper()} Whales</b>\n\n{msg}", parse_mode="HTML")
        return
    lines = [f"🐋 <b>{chain.upper()} Whale Transactions</b>\n"]
    for tx in valid[:5]:
        val = tx.get("value", 0)
        sym = tx.get("token_symbol", "?")
        addr = tx.get("from_address", "?")
        short_addr = f"{addr[:8]}...{addr[-4:]}" if len(addr) > 12 else addr
        lines.append(f"<b>{val} {sym}</b> — {short_addr}")
    lines.append(f"\n💡 Chains: {', '.join(VALID_CHAINS)}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await _get("/v1/market/news", {"limit": 5})
    if not data:
        await update.message.reply_text("Error. Try again.")
        return
    articles = data.get("articles", [])
    if not articles:
        await update.message.reply_text("No news available right now.")
        return
    lines = ["📰 <b>Latest Crypto News</b>\n"]
    for a in articles[:5]:
        title = a.get("title", "")[:80]
        source = a.get("source", "")
        url = a.get("url", "#")
        lines.append(f'• <a href="{url}">{title}</a>')
        lines.append(f"  <i>{source}</i>")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


# ---------- Price Alerts ----------

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /alert BTC above 70000\n\n"
            "Examples:\n"
            "/alert ETH below 3000\n"
            "/alert SOL above 200\n"
            "/alert BTC above 150000"
        )
        return
    coin = context.args[0].lower().strip()
    direction = context.args[1].lower().strip()
    try:
        target_price = float(context.args[2].replace(",", ""))
    except ValueError:
        await update.message.reply_text("Invalid price. Example: /alert BTC above 70000")
        return
    if direction not in ("above", "below"):
        await update.message.reply_text("Direction must be 'above' or 'below'.")
        return

    alert_id = _add_alert(update.effective_user.id, coin, direction, target_price)
    symbol = coin.upper()
    await update.message.reply_text(
        f"✅ Alert #{alert_id} created!\n\n"
        f"I'll notify you when {symbol} goes {direction} ${target_price:,.2f}"
    )


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = _load_alerts().get(str(update.effective_user.id), [])
    active = [a for a in alerts if not a.get("triggered")]
    if not active:
        await update.message.reply_text("No active alerts.\n\nUse /alert coin above|below price to set one.")
        return
    lines = ["🔔 <b>Your Active Alerts</b>\n"]
    for a in active:
        lines.append(f"#{a['id']} — <b>{a['coin'].upper()}</b> {a['direction']} ${a['target']:,.2f}")
    lines.append(f"\nTotal: {len(active)} alerts\nCancel: /cancel id")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cancel_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /cancel alert_id\nUse /alerts to see your alerts.")
        return
    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid alert ID. Use a number.")
        return
    removed = _remove_alert(update.effective_user.id, alert_id)
    if removed:
        await update.message.reply_text(f"Alert #{alert_id} removed.")
    else:
        await update.message.reply_text(f"Alert #{alert_id} not found.")


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    cmd = text.split()[0] if text else ""
    await update.message.reply_text(
        f"Unknown command: {cmd}\n\nType /start to see all available commands."
    )


async def non_command_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I only respond to commands.\n\nType /start to see all available commands."
    )


async def non_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "I can only process text commands.\n\nType /start to see all available commands."
    )


# ---------- Background alert checker ----------

async def check_alerts():
    """Periodically check prices and notify users of triggered alerts."""
    while True:
        try:
            await asyncio.sleep(120)
            alerts = _load_alerts()
            changed = False
            checked_coins: dict[str, float] = {}

            for uid, user_alerts in list(alerts.items()):
                for a in user_alerts:
                    if a.get("triggered"):
                        continue
                    coin = a["coin"]
                    if coin not in checked_coins:
                        data = await _get(f"/v1/market/coin/{coin}")
                        if data and "current_price" in data:
                            checked_coins[coin] = data["current_price"]
                        await asyncio.sleep(2)
                    price_now = checked_coins.get(coin)
                    if price_now is None:
                        continue
                    target = a["target"]
                    triggered = False
                    if a["direction"] == "above" and price_now >= target:
                        triggered = True
                    elif a["direction"] == "below" and price_now <= target:
                        triggered = True
                    if triggered:
                        a["triggered"] = True
                        changed = True
                        try:
                            bot = application.bot
                            await bot.send_message(
                                chat_id=int(uid),
                                text=(
                                    f"🔔 <b>Price Alert!</b>\n\n"
                                    f"<b>{coin.upper()}</b> is now <b>${price_now:,.2f}</b>\n"
                                    f"Your target: {a['direction']} ${target:,.2f}\n\n"
                                    f"Use /alerts to manage your alerts"
                                ),
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
            if changed:
                _save_alerts(alerts)
        except Exception:
            await asyncio.sleep(300)


# ---------- Handlers ----------

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
application.add_handler(CommandHandler("alert", alert))
application.add_handler(CommandHandler("alerts", list_alerts))
application.add_handler(CommandHandler("cancel", cancel_alert))
application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, non_command_text))
application.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, non_text_message))


@api.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url="https://crypto-insight-bot.onrender.com/webhook")
    asyncio.create_task(check_alerts())
    print("Bot started with webhook")


@api.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}


@api.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "running", "bot": "ChainSightBot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
