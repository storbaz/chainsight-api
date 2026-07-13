from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import market, defi, whales, health


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Unified Crypto Intelligence API — Prices, On-Chain Data, DeFi Analytics, and Sentiment in one place.",
        docs_url="/docs",
        redoc_url="/redoc",
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

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
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

    return app


app = create_app()
