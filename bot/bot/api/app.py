from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bot.config.settings import settings
from bot.api.routers import trades, portfolio, metrics, signals, backtests, status, ws


def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Bot API",
        version="1.0.0",
        description="Professional crypto trading bot dashboard API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(status.router, prefix="/api/v1", tags=["status"])
    app.include_router(trades.router, prefix="/api/v1", tags=["trades"])
    app.include_router(portfolio.router, prefix="/api/v1", tags=["portfolio"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
    app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
    app.include_router(backtests.router, prefix="/api/v1", tags=["backtests"])
    app.include_router(ws.router, tags=["websocket"])

    return app
