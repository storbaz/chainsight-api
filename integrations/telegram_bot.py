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
        "Commands:\n"
        "/price <coin> — Get coin price\n"
        "/top — Top 10 coins\n"
        "/feargreed — Fear & Greed Index\n"
        "/defi — Top DeFi protocols\n"
        "/gas — Ethereum gas prices\n"
        "/search <query> — Search coins\n\n"
        "💡 *Popular:* bitcoin, ethereum, solana, dogecoin, cardano",
        parse_mode="Markdown",
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /price bitcoin\n\n"
            "💡 Popular: bitcoin, ethereum, solana, dogecoin, cardano, ripple, litecoin"
        )
        return
    coin_id = context.args[0].lower().strip()
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/coin/{coin_id}")
        if resp.status_code == 404:
            suggestions = get_close_matches(coin_id, COMMON_COINS, n=3, cutoff=0.4)
            if suggestions:
                sug_text = ", ".join(suggestions)
                await update.message.reply_text(
                    f"❌ Coin '{coin_id}' not found.\n\nDid you mean: {sug_text}?"
                )
            else:
                await update.message.reply_text(
                    f"❌ Coin '{coin_id}' not found.\n\nTry: /search {coin_id}"
                )
            return
        data = resp.json()
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
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/top", params={"limit": 10})
        data = resp.json()
        if not data:
            await update.message.reply_text("⏳ Data loading. Try again in 30s.")
            return
        lines = ["📊 *Top 10 Cryptocurrencies*\n"]
        for i, coin in enumerate(data, 1):
            change = coin.get("price_change_percentage_24h", 0) or 0
            emoji = "🟢" if change >= 0 else "🔴"
            lines.append(f"{i}. *{coin['name']}* — ${coin['current_price']:,.2f} {emoji} {change:.1f}%")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


async def feargreed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/fear-greed")
        data = resp.json()
        value = data["value"]
        classification = data["classification"]
        emoji = "😱" if value <= 25 else "😨" if value <= 45 else "😐" if value <= 55 else "😊" if value <= 75 else "🤑"
        await update.message.reply_text(
            f"{emoji} *Fear & Greed Index*\n\nValue: *{value}*/100\nClassification: *{classification}*",
            parse_mode="Markdown",
        )
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


async def defi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/defi/protocols", params={"limit": 5})
        data = resp.json()
        lines = ["💰 *Top DeFi Protocols*\n"]
        for i, p in enumerate(data, 1):
            tvl = p.get("tvl", 0) or 0
            lines.append(f"{i}. *{p['name']}* — ${tvl/1e9:.2f}B TVL")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/whales/gas")
        data = resp.json()
        await update.message.reply_text(
            f"⛽ *Ethereum Gas Prices*\n\n"
            f"Low: {data['low']:.1f} Gwei\n"
            f"Average: {data['average']:.1f} Gwei\n"
            f"Fast: {data['fast']:.1f} Gwei",
            parse_mode="Markdown",
        )
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search bitcoin")
        return
    query = " ".join(context.args)
    try:
        resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/search", params={"query": query})
        data = resp.json()
        if not data:
            await update.message.reply_text(f"No results for '{query}'.")
            return
        lines = [f"🔍 *Results for '{query}'*\n"]
        for c in data[:5]:
            rank = c.get("market_cap_rank", "?")
            lines.append(f"• *{c['name']}* ({c['symbol'].upper()}) — Rank #{rank}")
        lines.append("\n💡 Use /price <id> to get details")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Error connecting to API. Try again.")


application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("price", price))
application.add_handler(CommandHandler("top", top))
application.add_handler(CommandHandler("feargreed", feargreed))
application.add_handler(CommandHandler("defi", defi))
application.add_handler(CommandHandler("gas", gas))
application.add_handler(CommandHandler("search", search))


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


@api.get("/")
async def root():
    return {"status": "running", "bot": "CryptoInsightBot"}
