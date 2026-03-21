"""
VectorBT optimization engine.
Runs a grid search over parameter combinations for the MomentumTrend strategy.
Uses vectorized operations — tests 1,400+ combos in seconds.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import vectorbt as vbt

from bot.backtest.metrics import (
    compute_all_metrics,
    compute_equity_curve,
    compute_monthly_returns,
    profit_factor,
    win_rate,
)
from bot.config.settings import settings
from bot.strategy.indicators.ema import ema
from bot.strategy.indicators.supertrend import supertrend, atr as atr_indicator
from bot.strategy.indicators.rsi import rsi
from bot.strategy.indicators.macd import macd
from bot.utils.logging import get_logger

logger = get_logger(__name__)

# Default parameter search space
DEFAULT_PARAM_RANGES = {
    "ema_fast": list(range(10, 31, 2)),     # [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
    "ema_slow": list(range(40, 81, 5)),     # [40, 45, 50, 55, 60, 65, 70, 75, 80]
    "st_mult": [2.0, 2.5, 3.0, 3.5, 4.0],  # 5 values
    "rsi_ob": [65.0, 70.0, 75.0],          # 3 values
}


def _compute_signals_for_params(
    df: pd.DataFrame,
    ema_fast: int,
    ema_slow: int,
    st_period: int,
    st_mult: float,
    rsi_period: int,
    rsi_ob: float,
    rsi_os: float,
    rsi_entry_min: float,
    rsi_entry_max: float,
    macd_fast: int,
    macd_slow: int,
    macd_sig: int,
) -> tuple[pd.Series, pd.Series]:
    """Compute long/short entry signals for a single parameter combination."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    ema_f = ema(close, ema_fast)
    ema_s = ema(close, ema_slow)

    # EMA cross
    above = ema_f > ema_s
    cross_up = above & ~above.shift(1).fillna(False)
    cross_down = ~above & above.shift(1).fillna(True)

    # Recent cross (this or previous bar)
    recent_cross_up = cross_up | cross_up.shift(1).fillna(False)
    recent_cross_down = cross_down | cross_down.shift(1).fillna(False)

    _, st_dir = supertrend(high, low, close, st_period, st_mult)
    rsi_vals = rsi(close, rsi_period)
    macd_l, macd_s_line, _ = macd(close, macd_fast, macd_slow, macd_sig)

    long_entry = (
        recent_cross_up
        & (ema_f > ema_s)
        & (st_dir == 1)
        & (rsi_vals >= rsi_entry_min)
        & (rsi_vals <= rsi_entry_max)
        & (macd_l > macd_s_line)
    )

    short_entry = (
        recent_cross_down
        & (ema_f < ema_s)
        & (st_dir == -1)
        & (rsi_vals >= rsi_entry_min)
        & (rsi_vals <= rsi_entry_max)
        & (macd_l < macd_s_line)
    )

    # Exits
    long_exit = (rsi_vals > rsi_ob) | (st_dir == -1)
    short_exit = (rsi_vals < rsi_os) | (st_dir == 1)

    return long_entry, short_entry, long_exit, short_exit


def run_vectorbt_optimization(
    df: pd.DataFrame,
    param_ranges: Optional[Dict[str, List]] = None,
    initial_capital: float = 10000.0,
    commission: float = 0.00055,
    top_n: int = 20,
    fixed_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Run grid search optimization over parameter combinations.

    Args:
        df: OHLCV DataFrame with open_time index and lowercase columns
        param_ranges: Dict of parameter name -> list of values to test
        initial_capital: Starting capital
        commission: Taker fee rate
        top_n: Return top N configurations by Sharpe ratio
        fixed_params: Parameters to hold constant

    Returns:
        List of top_n result dicts sorted by Sharpe ratio descending
    """
    if param_ranges is None:
        param_ranges = DEFAULT_PARAM_RANGES

    fp = fixed_params or {}
    st_period = fp.get("st_period", settings.supertrend_period)
    rsi_period = fp.get("rsi_period", settings.rsi_period)
    rsi_os = fp.get("rsi_os", settings.rsi_oversold)
    rsi_entry_min = fp.get("rsi_entry_min", settings.rsi_entry_min)
    rsi_entry_max = fp.get("rsi_entry_max", settings.rsi_entry_max)
    macd_fast = fp.get("macd_fast", settings.macd_fast)
    macd_slow_p = fp.get("macd_slow", settings.macd_slow)
    macd_sig = fp.get("macd_signal", settings.macd_signal_period)
    atr_sl_mult = fp.get("atr_sl_mult", settings.atr_sl_multiplier)
    atr_tp_mult = fp.get("atr_tp_mult", settings.atr_tp_multiplier)

    ema_fasts = param_ranges.get("ema_fast", [settings.ema_fast])
    ema_slows = param_ranges.get("ema_slow", [settings.ema_slow])
    st_mults = param_ranges.get("st_mult", [settings.supertrend_multiplier])
    rsi_obs = param_ranges.get("rsi_ob", [settings.rsi_overbought])

    results = []
    total = len(ema_fasts) * len(ema_slows) * len(st_mults) * len(rsi_obs)
    done = 0

    logger.info("vectorbt_optimization_start", total_combinations=total)

    for ef in ema_fasts:
        for es in ema_slows:
            if ef >= es:
                continue
            for sm in st_mults:
                for rob in rsi_obs:
                    try:
                        long_e, short_e, long_x, short_x = _compute_signals_for_params(
                            df,
                            ema_fast=ef,
                            ema_slow=es,
                            st_period=st_period,
                            st_mult=sm,
                            rsi_period=rsi_period,
                            rsi_ob=rob,
                            rsi_os=rsi_os,
                            rsi_entry_min=rsi_entry_min,
                            rsi_entry_max=rsi_entry_max,
                            macd_fast=macd_fast,
                            macd_slow=macd_slow_p,
                            macd_sig=macd_sig,
                        )

                        close = df["close"]

                        # ATR-based SL/TP using fixed multiples
                        atr_vals = atr_indicator(df["high"], df["low"], close, st_period)
                        sl_stop = atr_vals * atr_sl_mult / close
                        tp_stop = atr_vals * atr_tp_mult / close

                        # Fixed-fractional position sizing: risk risk_per_trade of
                        # initial capital per trade, sized to the ATR stop.
                        # size_units = (capital * risk%) / (price * sl%)
                        risk_per_trade = fp.get("risk_per_trade", settings.risk_per_trade)
                        sl_safe = sl_stop.replace(0, np.nan).ffill().fillna(0.02)
                        size_units = (initial_capital * risk_per_trade) / (close * sl_safe)
                        size_units = size_units.clip(upper=(initial_capital * 0.95) / close)

                        pf = vbt.Portfolio.from_signals(
                            close=close,
                            entries=long_e,
                            exits=long_x,
                            short_entries=short_e,
                            short_exits=short_x,
                            init_cash=initial_capital,
                            fees=commission,
                            sl_stop=sl_stop,
                            tp_stop=tp_stop,
                            size=size_units,
                            freq="60T",
                        )

                        stats = pf.stats()
                        total_ret = float(stats.get("Total Return [%]", 0))
                        sharpe = float(stats.get("Sharpe Ratio", 0))
                        max_dd = float(stats.get("Max Drawdown [%]", 0))
                        n_trades = int(stats.get("Total Trades", 0))
                        wr = float(stats.get("Win Rate [%]", 0))

                        results.append({
                            "ema_fast": ef,
                            "ema_slow": es,
                            "st_period": st_period,
                            "st_multiplier": sm,
                            "rsi_period": rsi_period,
                            "rsi_ob": rob,
                            "rsi_os": rsi_os,
                            "rsi_entry_min": rsi_entry_min,
                            "rsi_entry_max": rsi_entry_max,
                            "macd_fast": macd_fast,
                            "macd_slow": macd_slow_p,
                            "macd_signal": macd_sig,
                            "atr_sl_mult": atr_sl_mult,
                            "atr_tp_mult": atr_tp_mult,
                            "total_trades": n_trades,
                            "win_rate": wr,
                            "total_return": total_ret,
                            "max_drawdown": max_dd,
                            "sharpe_ratio": sharpe,
                            "profit_factor": 0,  # Computed separately if needed
                        })
                    except Exception as e:
                        logger.debug(
                            "vbt_combo_error",
                            ema_fast=ef, ema_slow=es, st_mult=sm, rsi_ob=rob,
                            error=str(e)
                        )

                    done += 1
                    if done % 100 == 0:
                        logger.info("vectorbt_progress", done=done, total=total)

    results.sort(key=lambda x: x.get("sharpe_ratio", 0), reverse=True)
    top = results[:top_n]

    logger.info(
        "vectorbt_optimization_complete",
        total_tested=len(results),
        top_sharpe=top[0]["sharpe_ratio"] if top else 0,
    )

    return top
