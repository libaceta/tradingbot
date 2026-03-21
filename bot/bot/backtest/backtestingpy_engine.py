"""
Detailed single-run backtest using Backtesting.py.
Mirrors the live MomentumTrendStrategy logic exactly.
Saves individual trades to DB with is_backtest=True.
"""
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from bot.backtest.metrics import (
    compute_all_metrics,
    compute_equity_curve,
    compute_monthly_returns,
)
from bot.config.settings import settings
from bot.strategy.indicators.ema import ema
from bot.strategy.indicators.supertrend import supertrend, atr
from bot.strategy.indicators.rsi import rsi as rsi_indicator
from bot.strategy.indicators.macd import macd
from bot.utils.logging import get_logger

logger = get_logger(__name__)


class _BTPyStrategy(Strategy):
    """Backtesting.py strategy class wrapping our MomentumTrend logic."""

    ema_fast: int = 21
    ema_slow: int = 55
    st_period: int = 10
    st_mult: float = 3.0
    rsi_period: int = 14
    rsi_ob: float = 70.0
    rsi_os: float = 30.0
    rsi_entry_min: float = 40.0
    rsi_entry_max: float = 60.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_sig: int = 9
    atr_sl_mult: float = 2.0
    atr_tp_mult: float = 3.0
    # Mode flags
    short_only: int = 0       # 1 = only take SHORT trades, skip LONGs
    no_rsi_filter: int = 0    # 1 = remove RSI 40-60 entry filter entirely
    # Regime filter: don't enter SHORT if price already dropped > max_drop_pct
    # from its recent peak (prevents shorting at local bottoms)
    regime_filter: int = 0        # 1 = enable regime filter
    max_drop_pct: float = 0.25    # max allowed drop from recent peak (0.25 = 25%)
    peak_lookback: int = 200      # bars to look back for recent peak
    # Futures / leverage (informational — actual leverage set via Backtest(margin=))
    futures_mode: int = 0
    leverage: int = 1
    # Long-term trend filter / bidirectional regime selector
    # trend_filter=1 + bidirectional=0 → block SHORT when price > MA (original)
    # trend_filter=1 + bidirectional=1 → LONG when price > MA, SHORT when price < MA
    # Default 4800 bars = 200 days on 1h candles (classic "200-day MA" filter)
    trend_filter: int = 0
    trend_ma_period: int = 4800
    bidirectional: int = 0   # 1 = LONG in bull + SHORT in bear (regime-aware)
    # Entry trigger mode:
    #   st_trigger=0 → original: EMA crossover (slow, lagging)
    #   st_trigger=1 → Supertrend flip as primary trigger + MACD confirmation
    #                  Faster, enters earlier in the move
    st_trigger: int = 0

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.df.index)
        high = pd.Series(self.data.High, index=self.data.df.index)
        low = pd.Series(self.data.Low, index=self.data.df.index)

        self.ema_f = self.I(lambda: ema(close, self.ema_fast).values, name="EMA_fast")
        self.ema_s = self.I(lambda: ema(close, self.ema_slow).values, name="EMA_slow")

        st_line, st_dir = supertrend(high, low, close, self.st_period, self.st_mult)
        self.st_line = self.I(lambda: st_line.values, name="Supertrend")
        self.st_dir = self.I(lambda: st_dir.values, name="ST_Dir")

        self.rsi_val = self.I(lambda: rsi_indicator(close, self.rsi_period).values, name="RSI")

        macd_l, macd_s, _ = macd(close, self.macd_fast, self.macd_slow, self.macd_sig)
        self.macd_line = self.I(lambda: macd_l.values, name="MACD")
        self.macd_sig_line = self.I(lambda: macd_s.values, name="MACD_sig")

        self.atr_val = self.I(
            lambda: atr(high, low, close, self.st_period).values, name="ATR"
        )

        # Rolling peak of high prices for regime filter
        rolling_peak = high.rolling(self.peak_lookback, min_periods=1).max()
        self.recent_peak = self.I(lambda: rolling_peak.values, name="Recent_Peak")

        # Long-term trend MA (200-day = 4800 bars on 1h data)
        trend_ma = close.rolling(self.trend_ma_period, min_periods=1).mean()
        self.trend_ma = self.I(lambda: trend_ma.values, name="Trend_MA")

    def next(self):
        price = self.data.Close[-1]
        cur_rsi = self.rsi_val[-1]
        cur_st_dir = self.st_dir[-1]
        cur_macd = self.macd_line[-1]
        cur_macd_sig = self.macd_sig_line[-1]
        cur_atr = self.atr_val[-1]

        ema_cross_up   = crossover(self.ema_f, self.ema_s)
        ema_cross_down = crossover(self.ema_s, self.ema_f)

        # Supertrend flip: direction changes this bar
        # (safe because backtesting.py only calls next() after enough warmup bars)
        st_prev        = self.st_dir[-2]
        st_flip_up     = (cur_st_dir == 1)  and (st_prev == -1)  # bearish → bullish
        st_flip_down   = (cur_st_dir == -1) and (st_prev == 1)   # bullish → bearish

        # Allow entry 1 bar after the flip too (catches missed signals)
        st_prev2 = self.st_dir[-3] if len(self.data) > 2 else st_prev
        recent_st_flip_up   = st_flip_up   or ((cur_st_dir == 1)  and (st_prev == 1)  and (st_prev2 == -1))
        recent_st_flip_down = st_flip_down or ((cur_st_dir == -1) and (st_prev == -1) and (st_prev2 == 1))

        rsi_ok_long  = self.no_rsi_filter or (self.rsi_entry_min <= cur_rsi <= self.rsi_entry_max)
        rsi_ok_short = self.no_rsi_filter or (self.rsi_entry_min <= cur_rsi <= self.rsi_entry_max)

        # Choose trigger mode
        if self.st_trigger:
            trigger_long  = recent_st_flip_up
            trigger_short = recent_st_flip_down
        else:
            trigger_long  = ema_cross_up
            trigger_short = ema_cross_down

        # Regime filter: skip SHORT if price already fell > max_drop_pct from recent peak
        if self.regime_filter:
            peak = self.recent_peak[-1]
            drop_from_peak = (peak - price) / peak if peak > 0 else 1.0
            regime_ok_short = drop_from_peak <= self.max_drop_pct
        else:
            regime_ok_short = True

        # ── Trend / regime filter ────────────────────────────────────────────
        # Requires trend_ma_period warmup bars before trusting the MA value.
        bar_idx = len(self.data.Close)
        ma_ready = bar_idx >= self.trend_ma_period
        cur_ma   = self.trend_ma[-1]
        above_ma = price > cur_ma   # True  → bull regime
        below_ma = price < cur_ma   # True  → bear regime

        if self.trend_filter and self.bidirectional:
            # Bidirectional: LONG only in bull, SHORT only in bear.
            # Block all trading until the MA is warmed up.
            trend_ok_long  = ma_ready and above_ma
            trend_ok_short = ma_ready and below_ma
        elif self.trend_filter:
            # Original single-direction filter: block SHORT in bull markets.
            trend_ok_long  = True
            trend_ok_short = ma_ready and below_ma
        else:
            trend_ok_long  = True
            trend_ok_short = True

        # In short_only mode, never open longs regardless of regime.
        if self.short_only:
            trend_ok_long = False

        trade_size = 0.95

        if not self.position:
            # ── LONG entry ──────────────────────────────────────────────────
            if (
                trend_ok_long
                and trigger_long
                and cur_st_dir == 1
                and rsi_ok_long
                and cur_macd > cur_macd_sig
            ):
                sl = price - self.atr_sl_mult * cur_atr
                tp = price + self.atr_tp_mult * cur_atr
                if sl > 0 and tp > sl:
                    self.buy(sl=sl, tp=tp, size=trade_size)

            # ── SHORT entry ─────────────────────────────────────────────────
            elif (
                trend_ok_short
                and trigger_short
                and cur_st_dir == -1
                and rsi_ok_short
                and regime_ok_short
                and cur_macd < cur_macd_sig
            ):
                sl = price + self.atr_sl_mult * cur_atr
                tp = price - self.atr_tp_mult * cur_atr
                if tp > 0 and sl > tp:
                    self.sell(sl=sl, tp=tp, size=trade_size)

        elif self.position.is_long:
            # LONG exit conditions
            if cur_rsi > self.rsi_ob or cur_st_dir == -1:
                self.position.close()

        elif self.position.is_short:
            # SHORT exit conditions
            if cur_rsi < self.rsi_os or cur_st_dir == 1:
                self.position.close()


def run_backtestingpy(
    df: pd.DataFrame,
    params: Dict[str, Any],
    initial_capital: float = 10000.0,
    commission: float = 0.00055,
) -> Dict[str, Any]:
    """
    Run a detailed backtest using Backtesting.py.
    df must have columns: Open, High, Low, Close, Volume (capitalized) and DatetimeIndex.
    """
    # Backtesting.py requires capitalized column names and DatetimeIndex
    ohlcv = df.copy()
    ohlcv.columns = [c.capitalize() for c in ohlcv.columns]

    # ---- Futures mode ----
    # Bybit perpetual futures allow fractional BTC. Backtesting.py only supports
    # integer units, so we scale prices to micro-BTC (1 unit = 0.001 BTC) to
    # allow small capital ($100+) to open positions.
    # Leverage is simulated via the 'margin' parameter: margin=1/leverage means
    # each unit of BTC only requires (1/leverage) of its value as collateral.
    futures_mode = int(params.get("futures_mode", 0))
    leverage = max(1, int(params.get("leverage", 1)))
    MICRO_SCALE = 1000  # 1 unit = 0.001 BTC

    if futures_mode:
        for col in ["Open", "High", "Low", "Close"]:
            ohlcv[col] = ohlcv[col] / MICRO_SCALE
        margin_fraction = 1.0 / leverage
        logger.info("futures_mode_enabled", leverage=leverage,
                    margin_pct=round(margin_fraction * 100, 1))
    else:
        margin_fraction = 1.0

    bt = Backtest(
        ohlcv,
        _BTPyStrategy,
        cash=initial_capital,
        commission=commission,
        margin=margin_fraction,
        exclusive_orders=True,
    )

    bt_params = {
        "ema_fast": params.get("ema_fast", settings.ema_fast),
        "ema_slow": params.get("ema_slow", settings.ema_slow),
        "st_period": params.get("st_period", settings.supertrend_period),
        "st_mult": params.get("st_multiplier", settings.supertrend_multiplier),
        "rsi_period": params.get("rsi_period", settings.rsi_period),
        "rsi_ob": params.get("rsi_ob", settings.rsi_overbought),
        "rsi_os": params.get("rsi_os", settings.rsi_oversold),
        "rsi_entry_min": params.get("rsi_entry_min", settings.rsi_entry_min),
        "rsi_entry_max": params.get("rsi_entry_max", settings.rsi_entry_max),
        "macd_fast": params.get("macd_fast", settings.macd_fast),
        "macd_slow": params.get("macd_slow", settings.macd_slow),
        "macd_sig": params.get("macd_signal", settings.macd_signal_period),
        "atr_sl_mult": params.get("atr_sl_mult", settings.atr_sl_multiplier),
        "atr_tp_mult": params.get("atr_tp_mult", settings.atr_tp_multiplier),
        "short_only": int(params.get("short_only", 0)),
        "no_rsi_filter": int(params.get("no_rsi_filter", 0)),
        "regime_filter": int(params.get("regime_filter", 0)),
        "max_drop_pct": float(params.get("max_drop_pct", 0.25)),
        "peak_lookback": int(params.get("peak_lookback", 200)),
        "trend_filter": int(params.get("trend_filter", 0)),
        "trend_ma_period": int(params.get("trend_ma_period", 4800)),
        "bidirectional": int(params.get("bidirectional", 0)),
        "st_trigger": int(params.get("st_trigger", 0)),
    }

    # Adjust SL/TP prices for micro-BTC scaling (they're computed inside the
    # strategy from ATR which is also scaled, so no change needed — handled
    # automatically since all OHLCV columns are divided by MICRO_SCALE).

    stats = bt.run(**bt_params)

    # Extract trades
    trades_df = stats._trades
    trades = []
    net_pnls = []
    r_multiples = []
    entry_times = []
    exit_times = []

    for _, row in trades_df.iterrows():
        entry_p = float(row["EntryPrice"])
        exit_p = float(row["ExitPrice"])
        size = float(row["Size"])
        direction = "LONG" if size > 0 else "SHORT"
        notional = abs(size) * entry_p

        gross = (exit_p - entry_p) * size
        fee = notional * commission * 2
        net = gross - fee

        entry_t = row["EntryTime"].to_pydatetime()
        exit_t = row["ExitTime"].to_pydatetime()
        duration = int((exit_t - entry_t).total_seconds())

        atr_at_entry = abs(entry_p - float(row.get("SL", entry_p))) / params.get("atr_sl_mult", 2.0) if row.get("SL") else 0
        risk_usdt = initial_capital * params.get("risk_per_trade", settings.risk_per_trade)
        r_mult = net / risk_usdt if risk_usdt > 0 else 0

        trades.append({
            "external_id": str(uuid.uuid4()),
            "direction": direction,
            "entry_price": entry_p,
            "exit_price": exit_p,
            "quantity": abs(size),
            "notional_usdt": notional,
            "entry_time": entry_t,
            "exit_time": exit_t,
            "gross_pnl": gross,
            "net_pnl": net,
            "pnl_pct": net / notional * 100 if notional else 0,
            "r_multiple": r_mult,
            "duration_secs": duration,
            "exit_reason": str(row.get("ExitBar", "SIGNAL")),
            "entry_fee": notional * commission,
            "exit_fee": abs(size) * exit_p * commission,
            "risk_usdt": risk_usdt,
        })
        net_pnls.append(net)
        r_multiples.append(r_mult)
        entry_times.append(entry_t)
        exit_times.append(exit_t)

    equity_curve_pts = compute_equity_curve(initial_capital, net_pnls, entry_times)
    monthly_returns = compute_monthly_returns(equity_curve_pts, initial_capital)
    final_equity = initial_capital + sum(net_pnls)

    perf_metrics = compute_all_metrics(
        initial_capital=initial_capital,
        final_equity=final_equity,
        net_pnls=net_pnls,
        r_multiples=r_multiples,
        entry_times=entry_times,
        exit_times=exit_times,
        equity_curve_points=equity_curve_pts,
    )

    logger.info(
        "backtestingpy_complete",
        trades=len(trades),
        total_return=perf_metrics.get("total_return"),
        sharpe=perf_metrics.get("sharpe_ratio"),
    )

    return {
        "metrics": perf_metrics,
        "trades": trades,
        "equity_curve": equity_curve_pts,
        "monthly_returns": monthly_returns,
    }
