from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Exchange ----
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    bybit_testnet: bool = True

    # ---- Trading Mode ----
    trading_mode: str = "testnet"  # testnet | live | paused

    # ---- Strategy ----
    strategy_name: str = "momentum_trend"  # momentum_trend | heikin_ashi_scalp
    trade_symbol: str = "BTCUSDT"
    trade_interval: int = 60  # minutes

    ema_fast: int = 21
    ema_slow: int = 55

    # Heikin Ashi Scalp strategy params
    ha_ema_period: int = 21
    ha_ema_trend_period: int = 200   # EMA macro trend filter (only trade with trend)
    ha_atr_min_pct: float = 0.003    # skip candles with ATR < 0.3% of price
    ha_cooldown_candles: int = 2     # candles to wait after any exit before re-entry

    supertrend_period: int = 10
    supertrend_multiplier: float = 3.0

    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_entry_min: float = 40.0
    rsi_entry_max: float = 60.0

    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal_period: int = 9

    atr_sl_multiplier: float = 1.0   # 1×ATR SL — más ajustado para scalping
    atr_tp_multiplier: float = 2.0   # 2×ATR TP — ratio R:R 1:2
    risk_per_trade: float = 0.02

    # ---- Risk Guards ----
    max_daily_loss_pct: float = 0.05
    max_open_positions: int = 3
    min_order_usdt: float = 10.0

    # ---- Database ----
    postgres_db: str = "tradingbot"
    postgres_user: str = "trader"
    postgres_password: str = "changeme"
    database_url: str = "postgresql+asyncpg://trader:changeme@db:5432/tradingbot"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:4200,http://localhost:80"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    # ---- Portfolio Snapshots ----
    snapshot_interval_secs: int = 300

    # ---- Logging ----
    log_level: str = "INFO"
    log_format: str = "json"  # json | pretty

    # ---- Backtesting ----
    backtest_default_capital: float = 10000.0
    backtest_commission: float = 0.00055

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        allowed = {"testnet", "live", "paused"}
        if v not in allowed:
            raise ValueError(f"trading_mode must be one of {allowed}")
        return v


# Singleton
settings = Settings()
