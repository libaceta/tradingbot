"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ohlcv
    op.create_table(
        "ohlcv",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(30, 8), nullable=False),
        sa.Column("turnover", sa.Numeric(30, 8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "interval", "open_time", name="uq_ohlcv_sym_int_time"),
    )
    op.create_index("ix_ohlcv_sym_int_time", "ohlcv", ["symbol", "interval", "open_time"])

    # signals
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("signal_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("ema_21", sa.Numeric(20, 8), nullable=True),
        sa.Column("ema_55", sa.Numeric(20, 8), nullable=True),
        sa.Column("ema_cross", sa.Boolean(), nullable=True),
        sa.Column("supertrend", sa.Numeric(20, 8), nullable=True),
        sa.Column("supertrend_dir", sa.String(10), nullable=True),
        sa.Column("rsi", sa.Numeric(10, 4), nullable=True),
        sa.Column("macd_line", sa.Numeric(20, 8), nullable=True),
        sa.Column("macd_signal", sa.Numeric(20, 8), nullable=True),
        sa.Column("macd_hist", sa.Numeric(20, 8), nullable=True),
        sa.Column("atr", sa.Numeric(20, 8), nullable=True),
        sa.Column("close_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("acted_on", sa.Boolean(), default=False),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_sym_time", "signals", ["symbol", "signal_time"])
    op.create_index("ix_signals_acted_time", "signals", ["acted_on", "created_at"])

    # backtest_runs
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_name", sa.String(200), nullable=True),
        sa.Column("engine", sa.String(30), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("interval", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", sa.Numeric(20, 8), nullable=False),
        sa.Column("ema_fast", sa.SmallInteger(), nullable=True),
        sa.Column("ema_slow", sa.SmallInteger(), nullable=True),
        sa.Column("st_period", sa.SmallInteger(), nullable=True),
        sa.Column("st_multiplier", sa.Numeric(6, 2), nullable=True),
        sa.Column("rsi_period", sa.SmallInteger(), nullable=True),
        sa.Column("rsi_ob", sa.Numeric(6, 2), nullable=True),
        sa.Column("rsi_os", sa.Numeric(6, 2), nullable=True),
        sa.Column("macd_fast", sa.SmallInteger(), nullable=True),
        sa.Column("macd_slow", sa.SmallInteger(), nullable=True),
        sa.Column("macd_signal", sa.SmallInteger(), nullable=True),
        sa.Column("atr_sl_mult", sa.Numeric(6, 2), nullable=True),
        sa.Column("atr_tp_mult", sa.Numeric(6, 2), nullable=True),
        sa.Column("risk_per_trade", sa.Numeric(6, 4), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("winning_trades", sa.Integer(), nullable=True),
        sa.Column("losing_trades", sa.Integer(), nullable=True),
        sa.Column("win_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("total_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("annualized_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 4), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("sortino_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("calmar_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("profit_factor", sa.Numeric(10, 4), nullable=True),
        sa.Column("avg_r_multiple", sa.Numeric(10, 4), nullable=True),
        sa.Column("avg_trade_duration_secs", sa.Integer(), nullable=True),
        sa.Column("total_fees_usdt", sa.Numeric(20, 8), nullable=True),
        sa.Column("final_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("equity_curve", JSONB, nullable=True),
        sa.Column("monthly_returns", JSONB, nullable=True),
        sa.Column("parameters_json", JSONB, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bt_runs_sym_engine", "backtest_runs", ["symbol", "engine", "created_at"])
    op.create_index("ix_bt_runs_sharpe", "backtest_runs", ["sharpe_ratio"])

    # trades
    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="OPEN"),
        sa.Column("entry_order_id", sa.String(64), nullable=True),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("entry_fee", sa.Numeric(20, 8), nullable=True),
        sa.Column("entry_fee_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("exit_order_id", sa.String(64), nullable=True),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("exit_fee", sa.Numeric(20, 8), nullable=True),
        sa.Column("exit_reason", sa.String(50), nullable=True),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("notional_usdt", sa.Numeric(20, 8), nullable=True),
        sa.Column("leverage", sa.SmallInteger(), default=1),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column("atr_at_entry", sa.Numeric(20, 8), nullable=True),
        sa.Column("risk_usdt", sa.Numeric(20, 8), nullable=True),
        sa.Column("gross_pnl", sa.Numeric(20, 8), nullable=True),
        sa.Column("net_pnl", sa.Numeric(20, 8), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("r_multiple", sa.Numeric(10, 4), nullable=True),
        sa.Column("duration_secs", sa.Integer(), nullable=True),
        sa.Column("signal_id", sa.BigInteger(), sa.ForeignKey("signals.id"), nullable=True),
        sa.Column("is_backtest", sa.Boolean(), default=False),
        sa.Column("backtest_id", sa.BigInteger(), sa.ForeignKey("backtest_runs.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_trades_sym_entry_time", "trades", ["symbol", "entry_time"])
    op.create_index("ix_trades_status_created", "trades", ["status", "created_at"])
    op.create_index("ix_trades_backtest", "trades", ["is_backtest", "backtest_id"])

    # portfolio_snapshots
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("available_usdt", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), default=0),
        sa.Column("realized_pnl_day", sa.Numeric(20, 8), default=0),
        sa.Column("open_positions", sa.SmallInteger(), default=0),
        sa.Column("peak_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("drawdown_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portfolio_snap_time", "portfolio_snapshots", ["snapshot_time"])


def downgrade() -> None:
    op.drop_table("portfolio_snapshots")
    op.drop_table("trades")
    op.drop_table("backtest_runs")
    op.drop_table("signals")
    op.drop_table("ohlcv")
