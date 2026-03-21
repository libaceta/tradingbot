from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# OHLCV — market data cache and backtest data source
# ---------------------------------------------------------------------------
class OHLCV(Base):
    __tablename__ = "ohlcv"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)  # "60", "240", "D"
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    turnover: Mapped[Optional[float]] = mapped_column(Numeric(30, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("symbol", "interval", "open_time", name="uq_ohlcv_sym_int_time"),
        Index("ix_ohlcv_sym_int_time", "symbol", "interval", "open_time"),
    )


# ---------------------------------------------------------------------------
# Signals — every evaluated signal, acted on or not
# ---------------------------------------------------------------------------
class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    signal_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG | SHORT | NONE

    # Indicator values at signal time
    ema_21: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    ema_55: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    ema_cross: Mapped[Optional[bool]] = mapped_column(Boolean)
    supertrend: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    supertrend_dir: Mapped[Optional[str]] = mapped_column(String(10))  # UP | DOWN
    rsi: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    macd_line: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    macd_signal: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    macd_hist: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    atr: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    close_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    acted_on: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="signal")

    __table_args__ = (
        Index("ix_signals_sym_time", "symbol", "signal_time"),
        Index("ix_signals_acted_time", "acted_on", "created_at"),
    )


# ---------------------------------------------------------------------------
# BacktestRuns — must be defined before Trade due to FK
# ---------------------------------------------------------------------------
class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_name: Mapped[Optional[str]] = mapped_column(String(200))
    engine: Mapped[str] = mapped_column(String(30), nullable=False)  # vectorbt | backtestingpy
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    # Strategy parameters
    ema_fast: Mapped[Optional[int]] = mapped_column(SmallInteger)
    ema_slow: Mapped[Optional[int]] = mapped_column(SmallInteger)
    st_period: Mapped[Optional[int]] = mapped_column(SmallInteger)
    st_multiplier: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    rsi_period: Mapped[Optional[int]] = mapped_column(SmallInteger)
    rsi_ob: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    rsi_os: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    macd_fast: Mapped[Optional[int]] = mapped_column(SmallInteger)
    macd_slow: Mapped[Optional[int]] = mapped_column(SmallInteger)
    macd_signal: Mapped[Optional[int]] = mapped_column(SmallInteger)
    atr_sl_mult: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    atr_tp_mult: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    risk_per_trade: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))

    # Performance metrics
    total_trades: Mapped[Optional[int]] = mapped_column(Integer)
    winning_trades: Mapped[Optional[int]] = mapped_column(Integer)
    losing_trades: Mapped[Optional[int]] = mapped_column(Integer)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    total_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    annualized_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    avg_trade_duration_secs: Mapped[Optional[int]] = mapped_column(Integer)
    total_fees_usdt: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    final_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))

    # Raw output (JSONB for equity curve and monthly returns)
    equity_curve: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    monthly_returns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    parameters_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="backtest_run")

    __table_args__ = (
        Index("ix_bt_runs_sym_engine", "symbol", "engine", "created_at"),
        Index("ix_bt_runs_sharpe", "sharpe_ratio"),
    )


# ---------------------------------------------------------------------------
# Trades — primary analytics table (live + backtest)
# ---------------------------------------------------------------------------
class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG | SHORT
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")

    # Entry
    entry_order_id: Mapped[Optional[str]] = mapped_column(String(64))
    entry_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    entry_fee: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    entry_fee_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 6))

    # Exit
    exit_order_id: Mapped[Optional[str]] = mapped_column(String(64))
    exit_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    exit_fee: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50))

    # Position sizing
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    notional_usdt: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    leverage: Mapped[int] = mapped_column(SmallInteger, default=1)

    # Risk levels at entry
    stop_loss: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    take_profit: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    atr_at_entry: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    risk_usdt: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))

    # Outcome
    gross_pnl: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    net_pnl: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    pnl_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    r_multiple: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer)

    # Links
    signal_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("signals.id"), nullable=True
    )
    is_backtest: Mapped[bool] = mapped_column(Boolean, default=False)
    backtest_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("backtest_runs.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    signal: Mapped[Optional["Signal"]] = relationship("Signal", back_populates="trades")
    backtest_run: Mapped[Optional["BacktestRun"]] = relationship(
        "BacktestRun", back_populates="trades"
    )

    __table_args__ = (
        Index("ix_trades_sym_entry_time", "symbol", "entry_time"),
        Index("ix_trades_status_created", "status", "created_at"),
        Index("ix_trades_backtest", "is_backtest", "backtest_id"),
    )


# ---------------------------------------------------------------------------
# PortfolioSnapshots — time-series equity curve
# ---------------------------------------------------------------------------
class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    equity_usdt: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    available_usdt: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    realized_pnl_day: Mapped[float] = mapped_column(Numeric(20, 8), default=0)
    open_positions: Mapped[int] = mapped_column(SmallInteger, default=0)
    peak_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    drawdown_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_portfolio_snap_time", "snapshot_time"),)
