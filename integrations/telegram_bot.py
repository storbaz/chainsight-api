"""ChainSight Telegram Bot — Webhook mode for free hosting."""

import os
import httpx
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

CHAINSIGHT_BASE = os.environ.get("CHAINSIGHT_BASE_URL", "https://chainsight-api.onrender.com")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
api = FastAPI()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *ChainSight Bot*\n\n"
        "Commands:\n"
        "/price <coin> — Get coin price\n"
        "/top — Top 10 coins\n"
        "/feargreed — Fear & Greed Index\n"
        "/defi — Top DeFi protocols\n"
        "/gas — Ethereum gas prices\n",
        parse_mode="Markdown",
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /price bitcoin")
        return
    coin_id = context.args[0].lower()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/coin/{coin_id}")
            if resp.status_code != 200:
                await update.message.reply_text("Coin not found.")
                return
            data = resp.json()
        await update.message.reply_text(
            f"💰 *{data['name']}* ({data['symbol'].upper()})\n\n"
            f"Price: ${data['current_price']:,.2f}\n"
            f"24h: {data['price_change_percentage_24h']:.2f}%\n"
            f"7d: {data.get('price_change_percentage_7d', 0):.2f}%\n"
            f"Market Cap: ${data['market_cap']:,.0f}\n"
            f"Rank: #{data['market_cap_rank']}",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/top", params={"limit": 10})
            data = resp.json()
        lines = ["📊 *Top 10 Cryptocurrencies*\n"]
        for i, coin in enumerate(data, 1):
            change = coin.get("price_change_percentage_24h", 0)
            emoji = "🟢" if change >= 0 else "🔴"
            lines.append(f"{i}. *{coin['name']}* — ${coin['current_price']:,.2f} {emoji} {change:.1f}%")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def feargreed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{CHAINSIGHT_BASE}/v1/market/fear-greed")
            data = resp.json()
        value = data["value"]
        classification = data["classification"]
        emoji = "😱" if value <= 25 else "😨" if value <= 45 else "😐" if value <= 55 else "😊" if value <= 75 else "🤑"
        await update.message.reply_text(
            f"{emoji} *Fear & Greed Index*\n\nValue: *{value}*/100\nClassification: *{classification}*",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def defi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{CHAINSIGHT_BASE}/v1/defi/protocols", params={"limit": 5})
            data = resp.json()
        lines = ["💰 *Top DeFi Protocols*\n"]
        for i, p in enumerate(data, 1):
            tvl = p.get("tvl", 0)
            lines.append(f"{i}. *{p['name']}* — ${tvl/1e9:.2f}B TVL")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{CHAINSIGHT_BASE}/v1/whales/gas")
            data = resp.json()
        await update.message.reply_text(
            f"⛽ *Ethereum Gas Prices*\n\n"
            f"Low: {data['low']:.1f} Gwei\n"
            f"Average: {data['average']:.1f} Gwei\n"
            f"Fast: {data['fast']:.1f} Gwei",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("price", price))
application.add_handler(CommandHandler("top", top))
application.add_handler(CommandHandler("feargreed", feargreed))
application.add_handler(CommandHandler("defi", defi))
application.add_handler(CommandHandler("gas", gas))


@api.on_event("startup")
async def startup():
    await application.initialize()
    await application.bot.set_webhook(url=f"https://crypto-insight-bot.onrender.com/webhook")
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
