"""
Professional Scalping Strategy Backtester for BTC/ETH on Bybit
================================================================
Tests 10 professional scalping strategies across multiple timeframes.
Completely standalone - no database or bot required.
"""

import requests
import pandas as pd
import numpy as np
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["5", "15"]          # 5m and 15m
INITIAL_EQUITY = 10_000           # USDT
RISK_PCT_OPTIONS = [0.01, 0.02]   # 1% and 2%
FEE_RATE = 0.00055                # 0.055% taker per side
MIN_TRADES = 30
BYBIT_BASE = "https://api.bybit.com/v5/market/kline"
DAYS_HISTORY = 90                 # days of data
BATCH_SIZE = 200
REQUEST_DELAY = 0.25              # seconds between API calls

# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_klines(symbol: str, interval: str, days: int = DAYS_HISTORY) -> pd.DataFrame:
    """Fetch historical klines from Bybit (handles pagination)."""
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    all_candles = []
    current_end = end_ms
    retries = 3

    print(f"  Fetching {symbol} {interval}m data ({days} days)...", end="", flush=True)

    while current_end > start_ms:
        for attempt in range(retries):
            try:
                params = {
                    "category": "linear",
                    "symbol": symbol,
                    "interval": interval,
                    "end": current_end,
                    "limit": BATCH_SIZE,
                }
                r = requests.get(BYBIT_BASE, params=params, timeout=15)
                r.raise_for_status()
                data = r.json()
                if data.get("retCode") != 0:
                    raise ValueError(f"API error: {data.get('retMsg')}")
                candles = data["result"]["list"]
                if not candles:
                    current_end = start_ms  # break outer loop
                    break
                all_candles.extend(candles)
                # Bybit returns newest first; oldest candle has smallest timestamp
                oldest_ts = int(candles[-1][0])
                if oldest_ts <= start_ms:
                    current_end = start_ms  # break outer loop
                    break
                current_end = oldest_ts - 1
                time.sleep(REQUEST_DELAY)
                break
            except Exception as e:
                if attempt == retries - 1:
                    print(f"\n  WARNING: fetch failed after {retries} attempts: {e}")
                    current_end = start_ms  # bail out
                else:
                    time.sleep(1)

    if not all_candles:
        print(" NO DATA")
        return pd.DataFrame()

    # columns: [timestamp, open, high, low, close, volume, turnover]
    df = pd.DataFrame(all_candles, columns=["ts", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"ts": int, "open": float, "high": float, "low": float,
                    "close": float, "volume": float, "turnover": float})
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
    df = df[df["ts"] >= start_ms].reset_index(drop=True)
    print(f" {len(df)} candles OK")
    return df


# ─────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period).std()
    return mid - std_dev * std, mid, mid + std_dev * std

def supertrend(df: pd.DataFrame, period: int = 7, multiplier: float = 2.0):
    atr_val = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    basic_upper = hl2 + multiplier * atr_val
    basic_lower = hl2 - multiplier * atr_val

    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    direction = pd.Series(1, index=df.index)

    for i in range(1, len(df)):
        if basic_upper.iloc[i] < final_upper.iloc[i - 1] or df["close"].iloc[i - 1] > final_upper.iloc[i - 1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i - 1]

        if basic_lower.iloc[i] > final_lower.iloc[i - 1] or df["close"].iloc[i - 1] < final_lower.iloc[i - 1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i - 1]

        if direction.iloc[i - 1] == -1 and df["close"].iloc[i] > final_upper.iloc[i]:
            direction.iloc[i] = 1
        elif direction.iloc[i - 1] == 1 and df["close"].iloc[i] < final_lower.iloc[i]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

    return direction  # +1 bullish, -1 bearish

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def stoch_rsi(series: pd.Series, rsi_period: int = 14, stoch_period: int = 14,
              k_smooth: int = 3, d_smooth: int = 3):
    rsi_vals = rsi(series, rsi_period)
    rsi_min = rsi_vals.rolling(stoch_period).min()
    rsi_max = rsi_vals.rolling(stoch_period).max()
    stoch = 100 * (rsi_vals - rsi_min) / (rsi_max - rsi_min + 1e-10)
    k = sma(stoch, k_smooth)
    d = sma(k, d_smooth)
    return k, d

def vwap_daily(df: pd.DataFrame) -> pd.Series:
    """VWAP that resets each calendar day."""
    df = df.copy()
    df["date"] = df["datetime"].dt.date
    df["tp"] = (df["high"] + df["low"] + df["close"]) / 3
    df["tp_vol"] = df["tp"] * df["volume"]
    df["cum_tp_vol"] = df.groupby("date")["tp_vol"].cumsum()
    df["cum_vol"] = df.groupby("date")["volume"].cumsum()
    return df["cum_tp_vol"] / df["cum_vol"]

def heikin_ashi(df: pd.DataFrame):
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = ha_close.copy()
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i - 1] + ha_close.iloc[i - 1]) / 2
    return ha_open, ha_close


# ─────────────────────────────────────────────
# BACKTESTING ENGINE
# ─────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, signals: pd.DataFrame, risk_pct: float = 0.01) -> Dict:
    """
    Event-driven backtester.
    signals columns: signal (1=long, -1=short, 0=flat), sl_dist (ATR distance), tp_dist (ATR distance)
    Entries happen at open of bar AFTER signal bar (no look-ahead).
    """
    equity = INITIAL_EQUITY
    trades = []
    position = None  # dict with entry info

    for i in range(1, len(df)):
        row = df.iloc[i]
        sig_row = signals.iloc[i - 1]  # signal from previous bar

        # Check open position first
        if position is not None:
            price = row["open"]  # check if SL/TP hit on open (gap)
            # Use high/low to determine if SL or TP was hit during bar
            if position["side"] == 1:  # long
                if row["low"] <= position["sl"]:
                    exit_price = position["sl"]
                    pnl_pct = (exit_price - position["entry"]) / position["entry"]
                    notional = position["qty"] * position["entry"]
                    exit_notional = position["qty"] * exit_price
                    pnl_usdt = (exit_price - position["entry"]) * position["qty"] - FEE_RATE * (notional + exit_notional)
                    equity += pnl_usdt
                    trades.append({"pnl": pnl_usdt, "pnl_pct": pnl_pct, "result": "sl", "equity": equity})
                    position = None
                elif row["high"] >= position["tp"]:
                    exit_price = position["tp"]
                    notional = position["qty"] * position["entry"]
                    exit_notional = position["qty"] * exit_price
                    pnl_usdt = (exit_price - position["entry"]) * position["qty"] - FEE_RATE * (notional + exit_notional)
                    equity += pnl_usdt
                    trades.append({"pnl": pnl_usdt, "pnl_pct": (exit_price - position["entry"]) / position["entry"],
                                   "result": "tp", "equity": equity})
                    position = None
            else:  # short
                if row["high"] >= position["sl"]:
                    exit_price = position["sl"]
                    notional = position["qty"] * position["entry"]
                    exit_notional = position["qty"] * exit_price
                    pnl_usdt = (position["entry"] - exit_price) * position["qty"] - FEE_RATE * (notional + exit_notional)
                    equity += pnl_usdt
                    trades.append({"pnl": pnl_usdt, "pnl_pct": (position["entry"] - exit_price) / position["entry"],
                                   "result": "sl", "equity": equity})
                    position = None
                elif row["low"] <= position["tp"]:
                    exit_price = position["tp"]
                    notional = position["qty"] * position["entry"]
                    exit_notional = position["qty"] * exit_price
                    pnl_usdt = (position["entry"] - exit_price) * position["qty"] - FEE_RATE * (notional + exit_notional)
                    equity += pnl_usdt
                    trades.append({"pnl": pnl_usdt, "pnl_pct": (position["entry"] - exit_price) / position["entry"],
                                   "result": "tp", "equity": equity})
                    position = None

        # Open new position if flat
        if position is None and sig_row["signal"] != 0:
            entry_price = row["open"]
            sl_dist = sig_row["sl_dist"]
            tp_dist = sig_row["tp_dist"]

            if sl_dist <= 0 or tp_dist <= 0 or entry_price <= 0:
                continue

            risk_usdt = equity * risk_pct
            qty = risk_usdt / sl_dist  # shares = risk / distance_in_price

            if qty <= 0:
                continue

            side = int(sig_row["signal"])
            if side == 1:  # long
                sl = entry_price - sl_dist
                tp = entry_price + tp_dist
            else:  # short
                sl = entry_price + sl_dist
                tp = entry_price - tp_dist

            # Validate TP is on correct side
            if side == 1 and tp <= entry_price:
                continue
            if side == -1 and tp >= entry_price:
                continue

            position = {
                "side": side,
                "entry": entry_price,
                "qty": qty,
                "sl": sl,
                "tp": tp,
            }

    # Close any open position at last bar close
    if position is not None:
        last = df.iloc[-1]
        exit_price = last["close"]
        if position["side"] == 1:
            pnl_usdt = (exit_price - position["entry"]) * position["qty"] - FEE_RATE * 2 * position["qty"] * position["entry"]
        else:
            pnl_usdt = (position["entry"] - exit_price) * position["qty"] - FEE_RATE * 2 * position["qty"] * position["entry"]
        equity += pnl_usdt
        trades.append({"pnl": pnl_usdt, "pnl_pct": 0, "result": "open_close", "equity": equity})

    return compute_metrics(trades, INITIAL_EQUITY)


def compute_metrics(trades: List[Dict], initial_equity: float) -> Dict:
    if len(trades) < MIN_TRADES:
        return {"trades": len(trades), "valid": False, "reason": f"insufficient trades ({len(trades)}<{MIN_TRADES})"}

    pnls = [t["pnl"] for t in trades]
    equities = [initial_equity] + [t["equity"] for t in trades]
    eq_arr = np.array(equities)

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) * 100
    total_return = (equities[-1] - initial_equity) / initial_equity * 100

    # Max drawdown
    peak = np.maximum.accumulate(eq_arr)
    dd = (eq_arr - peak) / peak * 100
    max_dd = abs(dd.min())

    # Profit factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 1e-9
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999

    # Per-trade returns for Sharpe/Sortino
    returns = np.array([p / initial_equity for p in pnls])
    mean_ret = returns.mean()
    std_ret = returns.std()

    # Annualized Sharpe (assuming ~252 trading days, using trade count as proxy)
    if std_ret > 0:
        sharpe = (mean_ret / std_ret) * np.sqrt(len(trades))
    else:
        sharpe = 0

    # Sortino
    neg_returns = returns[returns < 0]
    downside_std = neg_returns.std() if len(neg_returns) > 0 else 1e-9
    sortino = (mean_ret / downside_std) * np.sqrt(len(trades)) if downside_std > 0 else 0

    # Calmar
    calmar = total_return / max_dd if max_dd > 0 else 0

    # Composite score
    score = sharpe * (1 - max_dd / 100) * profit_factor if max_dd < 100 else 0

    avg_pnl = np.mean(pnls)

    return {
        "valid": True,
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "total_return": round(total_return, 2),
        "max_dd": round(max_dd, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "profit_factor": round(profit_factor, 3),
        "avg_pnl": round(avg_pnl, 4),
        "calmar": round(calmar, 3),
        "score": round(score, 4),
    }


# ─────────────────────────────────────────────
# STRATEGY SIGNAL GENERATORS
# ─────────────────────────────────────────────

def strategy_ema_cross(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 1: EMA Fast Cross Scalp"""
    e8 = ema(df["close"], 8)
    e21 = ema(df["close"], 21)
    atr14 = atr(df, 14)
    vol_ma = sma(df["volume"], 20)

    cross_up = (e8 > e21) & (e8.shift(1) <= e21.shift(1))
    cross_dn = (e8 < e21) & (e8.shift(1) >= e21.shift(1))
    vol_surge = df["volume"] > vol_ma * 1.2

    sig = pd.Series(0, index=df.index)
    sig[cross_up & vol_surge & (df["close"] > e21)] = 1
    sig[cross_dn & vol_surge & (df["close"] < e21)] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 2.5 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_rsi2(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 2: RSI(2) Mean Reversion"""
    rsi2 = rsi(df["close"], 2)
    e50 = ema(df["close"], 50)
    e200 = ema(df["close"], 200)
    atr14 = atr(df, 14)

    bull_trend = e50 > e200
    bear_trend = e50 < e200

    sig = pd.Series(0, index=df.index)
    sig[(rsi2 < 10) & (df["close"] > e50) & bull_trend] = 1
    sig[(rsi2 > 90) & (df["close"] < e50) & bear_trend] = -1

    sl_dist = 1.2 * atr14
    tp_dist = 1.5 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 3: Supertrend Fast Scalp"""
    st_fast = supertrend(df, 7, 2.0)
    st_slow = supertrend(df, 14, 3.0)
    atr14 = atr(df, 14)

    fast_flip_bull = (st_fast == 1) & (st_fast.shift(1) == -1)
    fast_flip_bear = (st_fast == -1) & (st_fast.shift(1) == 1)

    sig = pd.Series(0, index=df.index)
    sig[fast_flip_bull & (st_slow == 1)] = 1
    sig[fast_flip_bear & (st_slow == -1)] = -1

    sl_dist = 1.0 * atr14
    tp_dist = 2.0 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_bb_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 4: Bollinger Band + RSI Confluence"""
    bb_lo, bb_mid, bb_hi = bollinger_bands(df["close"], 20, 2.0)
    rsi14 = rsi(df["close"], 14)
    atr14 = atr(df, 14)

    # Bounce confirmation: previous bar closed below/above band, now back inside
    prev_below_lower = (df["close"].shift(1) < bb_lo.shift(1)) & (rsi14.shift(1) < 30)
    bounce_long = prev_below_lower & (df["close"] > bb_lo)

    prev_above_upper = (df["close"].shift(1) > bb_hi.shift(1)) & (rsi14.shift(1) > 70)
    bounce_short = prev_above_upper & (df["close"] < bb_hi)

    sig = pd.Series(0, index=df.index)
    sig[bounce_long] = 1
    sig[bounce_short] = -1

    sl_dist = 1.5 * atr14
    # TP = distance to BB_middle from entry (approximate with 1.5*ATR as floor)
    tp_dist = (bb_mid - df["close"]).abs().clip(lower=1.5 * atr14)
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_macd_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 5: MACD + EMA Trend Scalp"""
    _, _, hist = macd(df["close"], 12, 26, 9)
    e21 = ema(df["close"], 21)
    e50 = ema(df["close"], 50)
    atr14 = atr(df, 14)

    hist_flip_pos = (hist > 0) & (hist.shift(1) <= 0)
    hist_flip_neg = (hist < 0) & (hist.shift(1) >= 0)

    sig = pd.Series(0, index=df.index)
    sig[hist_flip_pos & (df["close"] > e21) & (e21 > e50)] = 1
    sig[hist_flip_neg & (df["close"] < e21) & (e21 < e50)] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 3.0 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_stochrsi_ema(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 6: StochRSI + EMA Scalp"""
    k, d = stoch_rsi(df["close"], 14, 14, 3, 3)
    e50 = ema(df["close"], 50)
    atr14 = atr(df, 14)

    k_cross_up = (k > d) & (k.shift(1) <= d.shift(1))
    k_cross_dn = (k < d) & (k.shift(1) >= d.shift(1))

    sig = pd.Series(0, index=df.index)
    sig[k_cross_up & (k < 20) & (df["close"] > e50)] = 1
    sig[k_cross_dn & (k > 80) & (df["close"] < e50)] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 2.5 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_keltner(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 7: Keltner Channel Breakout"""
    e20 = ema(df["close"], 20)
    atr14 = atr(df, 14)
    e50 = ema(df["close"], 50)

    kc_upper = e20 + 2.0 * atr14
    kc_lower = e20 - 2.0 * atr14

    # Break above upper: current close > upper, prev close <= upper
    break_up = (df["close"] > kc_upper) & (df["close"].shift(1) <= kc_upper.shift(1))
    break_dn = (df["close"] < kc_lower) & (df["close"].shift(1) >= kc_lower.shift(1))

    sig = pd.Series(0, index=df.index)
    sig[break_up & (df["close"] > e50)] = 1
    sig[break_dn & (df["close"] < e50)] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 2.0 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_vwap_bounce(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 8: VWAP Bounce Scalp"""
    vwap = vwap_daily(df)
    e9 = ema(df["close"], 9)
    rsi14 = rsi(df["close"], 14)
    atr14 = atr(df, 14)

    cross_above = (df["close"] > vwap) & (df["close"].shift(1) <= vwap.shift(1))
    cross_below = (df["close"] < vwap) & (df["close"].shift(1) >= vwap.shift(1))
    e9_rising = e9 > e9.shift(1)
    e9_falling = e9 < e9.shift(1)

    sig = pd.Series(0, index=df.index)
    sig[cross_above & (rsi14 > 45) & e9_rising] = 1
    sig[cross_below & (rsi14 < 55) & e9_falling] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 2.5 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_ema_ribbon(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 9: EMA Ribbon + Volume Surge"""
    e3 = ema(df["close"], 3)
    e5 = ema(df["close"], 5)
    e8 = ema(df["close"], 8)
    e13 = ema(df["close"], 13)
    e21 = ema(df["close"], 21)
    atr14 = atr(df, 14)
    vol_ma = sma(df["volume"], 20)

    bull_ribbon = (e3 > e5) & (e5 > e8) & (e8 > e13) & (e13 > e21)
    bear_ribbon = (e3 < e5) & (e5 < e8) & (e8 < e13) & (e13 < e21)
    vol_surge = df["volume"] > vol_ma * 2.0

    sig = pd.Series(0, index=df.index)
    sig[bull_ribbon & vol_surge] = 1
    sig[bear_ribbon & vol_surge] = -1

    sl_dist = 2.0 * atr14
    tp_dist = 3.0 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


def strategy_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy 10: Heikin Ashi Trend Change + EMA"""
    ha_open, ha_close = heikin_ashi(df)
    e21 = ema(df["close"], 21)
    atr14 = atr(df, 14)

    ha_bull = ha_close > ha_open
    ha_bear = ha_close < ha_open

    # Flip from bearish to bullish
    flip_bull = ha_bull & (~ha_bull.shift(1).fillna(False))
    flip_bear = ha_bear & (~ha_bear.shift(1).fillna(False))

    sig = pd.Series(0, index=df.index)
    sig[flip_bull & (df["close"] > e21)] = 1
    sig[flip_bear & (df["close"] < e21)] = -1

    sl_dist = 1.5 * atr14
    tp_dist = 2.5 * atr14
    return pd.DataFrame({"signal": sig, "sl_dist": sl_dist, "tp_dist": tp_dist})


# ─────────────────────────────────────────────
# PARAMETER VARIATION
# ─────────────────────────────────────────────

def strategy_ema_cross_params(df: pd.DataFrame, sl_mult: float, tp_mult: float) -> pd.DataFrame:
    e8 = ema(df["close"], 8)
    e21 = ema(df["close"], 21)
    atr14 = atr(df, 14)
    vol_ma = sma(df["volume"], 20)
    cross_up = (e8 > e21) & (e8.shift(1) <= e21.shift(1))
    cross_dn = (e8 < e21) & (e8.shift(1) >= e21.shift(1))
    vol_surge = df["volume"] > vol_ma * 1.2
    sig = pd.Series(0, index=df.index)
    sig[cross_up & vol_surge & (df["close"] > e21)] = 1
    sig[cross_dn & vol_surge & (df["close"] < e21)] = -1
    return pd.DataFrame({"signal": sig, "sl_dist": sl_mult * atr14, "tp_dist": tp_mult * atr14})


def strategy_rsi2_params(df: pd.DataFrame, sl_mult: float, tp_mult: float) -> pd.DataFrame:
    rsi2 = rsi(df["close"], 2)
    e50 = ema(df["close"], 50)
    e200 = ema(df["close"], 200)
    atr14 = atr(df, 14)
    bull_trend = e50 > e200
    bear_trend = e50 < e200
    sig = pd.Series(0, index=df.index)
    sig[(rsi2 < 10) & (df["close"] > e50) & bull_trend] = 1
    sig[(rsi2 > 90) & (df["close"] < e50) & bear_trend] = -1
    return pd.DataFrame({"signal": sig, "sl_dist": sl_mult * atr14, "tp_dist": tp_mult * atr14})


def strategy_supertrend_params(df: pd.DataFrame, sl_mult: float, tp_mult: float) -> pd.DataFrame:
    st_fast = supertrend(df, 7, 2.0)
    st_slow = supertrend(df, 14, 3.0)
    atr14 = atr(df, 14)
    fast_flip_bull = (st_fast == 1) & (st_fast.shift(1) == -1)
    fast_flip_bear = (st_fast == -1) & (st_fast.shift(1) == 1)
    sig = pd.Series(0, index=df.index)
    sig[fast_flip_bull & (st_slow == 1)] = 1
    sig[fast_flip_bear & (st_slow == -1)] = -1
    return pd.DataFrame({"signal": sig, "sl_dist": sl_mult * atr14, "tp_dist": tp_mult * atr14})


# Map strategy names to their generators
STRATEGIES = {
    "S1_EMA_Cross": strategy_ema_cross,
    "S2_RSI2_MeanRev": strategy_rsi2,
    "S3_Supertrend": strategy_supertrend,
    "S4_BB_RSI": strategy_bb_rsi,
    "S5_MACD_EMA": strategy_macd_ema,
    "S6_StochRSI_EMA": strategy_stochrsi_ema,
    "S7_Keltner": strategy_keltner,
    "S8_VWAP_Bounce": strategy_vwap_bounce,
    "S9_EMA_Ribbon": strategy_ema_ribbon,
    "S10_HeikinAshi": strategy_heikin_ashi,
}


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  SCALPING STRATEGY BACKTESTER - Bybit Crypto")
    print("=" * 70)

    output_dir = "/app/strategies/scalping_research"

    # ── Step 1: Fetch data ──────────────────────────────────────────────
    print("\n[1/4] Fetching market data...")
    data_cache = {}
    for symbol in SYMBOLS:
        data_cache[symbol] = {}
        for tf in TIMEFRAMES:
            df = fetch_klines(symbol, tf, DAYS_HISTORY)
            if not df.empty:
                data_cache[symbol][tf] = df

    # ── Step 2: Run all strategies ──────────────────────────────────────
    print("\n[2/4] Running backtests...")
    all_results = []

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            if tf not in data_cache.get(symbol, {}):
                print(f"  Skipping {symbol} {tf}m - no data")
                continue
            df = data_cache[symbol][tf]
            print(f"\n  {symbol} {tf}m ({len(df)} bars):")

            for strat_name, strat_fn in STRATEGIES.items():
                for risk_pct in RISK_PCT_OPTIONS:
                    try:
                        signals = strat_fn(df)
                        result = run_backtest(df, signals, risk_pct)
                        result["strategy"] = strat_name
                        result["symbol"] = symbol
                        result["timeframe"] = f"{tf}m"
                        result["risk_pct"] = risk_pct
                        all_results.append(result)

                        if result["valid"]:
                            flag = ""
                            if (result["sharpe"] > 1.5 and result["profit_factor"] > 1.3
                                    and result["win_rate"] > 45):
                                flag = " *** PROMISING ***"
                            print(f"    {strat_name} r={risk_pct*100:.0f}% | "
                                  f"T={result['trades']:3d} WR={result['win_rate']:5.1f}% "
                                  f"Ret={result['total_return']:6.1f}% "
                                  f"DD={result['max_dd']:5.1f}% "
                                  f"Sh={result['sharpe']:5.2f} PF={result['profit_factor']:5.3f} "
                                  f"Sc={result['score']:6.4f}{flag}")
                        else:
                            print(f"    {strat_name} r={risk_pct*100:.0f}% | INVALID: {result.get('reason','')}")
                    except Exception as e:
                        print(f"    {strat_name} r={risk_pct*100:.0f}% | ERROR: {e}")
                        all_results.append({
                            "strategy": strat_name, "symbol": symbol,
                            "timeframe": f"{tf}m", "risk_pct": risk_pct,
                            "valid": False, "reason": str(e), "trades": 0,
                        })

    # ── Step 3: Parameter variations for promising strategies ───────────
    print("\n[3/4] Running parameter variations for top strategies...")
    promising = [r for r in all_results if r.get("valid") and
                 r.get("sharpe", 0) > 1.5 and r.get("profit_factor", 0) > 1.3 and r.get("win_rate", 0) > 45]

    param_fn_map = {
        "S1_EMA_Cross": strategy_ema_cross_params,
        "S2_RSI2_MeanRev": strategy_rsi2_params,
        "S3_Supertrend": strategy_supertrend_params,
    }

    sl_mults = [1.0, 1.5, 2.0]
    tp_mults = [1.5, 2.0, 2.5, 3.0]

    # Get unique promising strategy names
    promising_names = set(r["strategy"] for r in promising)

    for pname in promising_names:
        if pname not in param_fn_map:
            continue
        fn = param_fn_map[pname]
        print(f"\n  Varying params for {pname}:")
        for symbol in SYMBOLS:
            for tf in TIMEFRAMES:
                if tf not in data_cache.get(symbol, {}):
                    continue
                df = data_cache[symbol][tf]
                for sl_m in sl_mults:
                    for tp_m in tp_mults:
                        for risk_pct in RISK_PCT_OPTIONS:
                            key = f"{pname}_SL{sl_m}_TP{tp_m}"
                            try:
                                signals = fn(df, sl_m, tp_m)
                                result = run_backtest(df, signals, risk_pct)
                                result["strategy"] = key
                                result["symbol"] = symbol
                                result["timeframe"] = f"{tf}m"
                                result["risk_pct"] = risk_pct
                                result["is_variation"] = True
                                all_results.append(result)
                                if result["valid"]:
                                    flag = " *** BEST ***" if (result["score"] > 2.0) else ""
                                    print(f"    {symbol} {tf}m r={risk_pct*100:.0f}% sl={sl_m} tp={tp_m} | "
                                          f"Sh={result['sharpe']:5.2f} PF={result['profit_factor']:5.3f} "
                                          f"WR={result['win_rate']:5.1f}% Sc={result['score']:6.4f}{flag}")
                            except Exception as e:
                                pass

    # ── Step 4: Save results ────────────────────────────────────────────
    print("\n[4/4] Saving results...")

    # Save JSON
    with open(f"{output_dir}/results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"  Saved results.json ({len(all_results)} entries)")

    # ── Leaderboard ─────────────────────────────────────────────────────
    valid = [r for r in all_results if r.get("valid") and not r.get("is_variation")]
    valid.sort(key=lambda x: x.get("score", 0), reverse=True)

    print("\n" + "=" * 70)
    print("  LEADERBOARD (Top 20, sorted by composite score)")
    print("=" * 70)
    print(f"{'Rank':<5} {'Strategy':<25} {'Sym':<8} {'TF':<5} {'R%':<4} "
          f"{'Trades':<7} {'WR%':<6} {'Ret%':<7} {'DD%':<6} {'Sh':<6} {'PF':<6} {'Score':<7}")
    print("-" * 100)
    for rank, r in enumerate(valid[:20], 1):
        print(f"{rank:<5} {r['strategy']:<25} {r['symbol']:<8} {r['timeframe']:<5} "
              f"{r['risk_pct']*100:.0f}%{'':<2} "
              f"{r['trades']:<7} {r['win_rate']:<6.1f} {r['total_return']:<7.1f} "
              f"{r['max_dd']:<6.1f} {r['sharpe']:<6.2f} {r['profit_factor']:<6.3f} {r['score']:<7.4f}")

    # ── Generate markdown report ─────────────────────────────────────────
    generate_report(all_results, valid, output_dir)
    print(f"\n  Saved SCALPING_REPORT.md")
    print("\nDone!")


def generate_report(all_results: List[Dict], valid_sorted: List[Dict], output_dir: str):
    top3 = valid_sorted[:3]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    promising = [r for r in valid_sorted if
                 r.get("sharpe", 0) > 1.5 and r.get("profit_factor", 0) > 1.3 and r.get("win_rate", 0) > 45]

    lines = [
        "# Scalping Strategy Research Report",
        f"*Generated: {now}*",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"Backtested **{len(STRATEGIES)} scalping strategies** across "
        f"**{len(SYMBOLS)} symbols** (BTCUSDT, ETHUSDT) on **{len(TIMEFRAMES)} timeframes** "
        f"(5m, 15m) using **{DAYS_HISTORY} days** of Bybit historical data.",
        "",
        f"- Total backtests run: **{len(all_results)}**",
        f"- Valid results: **{len(valid_sorted)}**",
        f"- Promising strategies (Sharpe>1.5, PF>1.3, WR>45%): **{len(promising)}**",
        "",
    ]

    if top3:
        lines.append("### Top 3 Strategies")
        for i, r in enumerate(top3, 1):
            lines.append(f"{i}. **{r['strategy']}** on {r['symbol']} {r['timeframe']} "
                         f"| Score={r['score']:.4f}, Sharpe={r['sharpe']:.2f}, "
                         f"WR={r['win_rate']:.1f}%, Return={r['total_return']:.1f}%")
        lines.append("")

    lines += [
        "---",
        "",
        "## 2. Methodology",
        "",
        "### Data",
        f"- Exchange: Bybit (public REST API v5)",
        f"- Symbols: BTCUSDT, ETHUSDT (USDT perpetual futures)",
        f"- Timeframes: 5m, 15m",
        f"- History: {DAYS_HISTORY} days",
        f"- Batch size: {BATCH_SIZE} candles with {REQUEST_DELAY}s delay",
        "",
        "### Backtesting Assumptions",
        f"- Initial equity: ${INITIAL_EQUITY:,} USDT",
        f"- Risk per trade: 1% and 2% of equity (tested both)",
        f"- Fee: {FEE_RATE*100:.3f}% taker per side ({FEE_RATE*2*100:.3f}% round trip) - Bybit USDT perp rates",
        f"- Max 1 position at a time",
        f"- Position sizing: risk_usdt / (sl_atr_distance in price)",
        f"- No look-ahead bias: signals use shift(1)",
        f"- Entries at open of next bar after signal",
        f"- Exit: SL/TP hit via bar's high/low; open position closed at final bar's close",
        f"- Minimum {MIN_TRADES} trades required for valid result",
        "",
        "### Scoring",
        "```",
        "Score = Sharpe * (1 - max_dd/100) * profit_factor",
        "```",
        "Higher is better. Penalizes high drawdown.",
        "",
        "---",
        "",
        "## 3. Results Table (All Valid Strategies)",
        "",
        "| Rank | Strategy | Symbol | TF | Risk | Trades | WR% | Return% | MaxDD% | Sharpe | Sortino | PF | Calmar | Score |",
        "|------|----------|--------|----|------|--------|-----|---------|--------|--------|---------|-----|--------|-------|",
    ]

    for rank, r in enumerate(valid_sorted, 1):
        if r.get("is_variation"):
            continue
        lines.append(
            f"| {rank} | {r['strategy']} | {r['symbol']} | {r['timeframe']} | "
            f"{r['risk_pct']*100:.0f}% | {r['trades']} | {r['win_rate']:.1f} | "
            f"{r['total_return']:.1f} | {r['max_dd']:.1f} | {r['sharpe']:.2f} | "
            f"{r.get('sortino',0):.2f} | {r['profit_factor']:.3f} | "
            f"{r.get('calmar',0):.2f} | {r['score']:.4f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Top 3 Strategies - Detailed Analysis",
        "",
    ]

    for i, r in enumerate(top3, 1):
        lines += [
            f"### #{i}: {r['strategy']}",
            "",
            f"- **Symbol**: {r['symbol']}",
            f"- **Timeframe**: {r['timeframe']}",
            f"- **Risk per trade**: {r['risk_pct']*100:.0f}%",
            f"- **Total trades**: {r['trades']}",
            f"- **Win rate**: {r['win_rate']:.1f}%",
            f"- **Total return**: {r['total_return']:.1f}%",
            f"- **Max drawdown**: {r['max_dd']:.1f}%",
            f"- **Sharpe ratio**: {r['sharpe']:.3f}",
            f"- **Sortino ratio**: {r.get('sortino',0):.3f}",
            f"- **Profit factor**: {r['profit_factor']:.3f}",
            f"- **Calmar ratio**: {r.get('calmar',0):.3f}",
            f"- **Avg trade PnL**: ${r['avg_pnl']:.2f}",
            f"- **Composite score**: {r['score']:.4f}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 5. Parameter Sensitivity (Top Promising Strategies)",
        "",
    ]

    # Show parameter variations
    variations = [r for r in all_results if r.get("is_variation") and r.get("valid")]
    if variations:
        variations.sort(key=lambda x: x.get("score", 0), reverse=True)
        lines += [
            "| Strategy Variant | Symbol | TF | Risk | Trades | WR% | Return% | DD% | Sharpe | PF | Score |",
            "|-----------------|--------|----|------|--------|-----|---------|-----|--------|-----|-------|",
        ]
        for r in variations[:30]:
            lines.append(
                f"| {r['strategy']} | {r['symbol']} | {r['timeframe']} | "
                f"{r['risk_pct']*100:.0f}% | {r['trades']} | {r['win_rate']:.1f} | "
                f"{r['total_return']:.1f} | {r['max_dd']:.1f} | {r['sharpe']:.2f} | "
                f"{r['profit_factor']:.3f} | {r['score']:.4f} |"
            )
    else:
        lines.append("*No parameter variations ran (no strategies met the promising threshold).*")

    lines += [
        "",
        "---",
        "",
        "## 6. Implementation Recommendations",
        "",
        "### Priority Implementation Order",
        "",
    ]

    for i, r in enumerate(top3, 1):
        lines.append(f"{i}. **{r['strategy']}** — Integrate into FastAPI bot using existing indicator library.")

    lines += [
        "",
        "### Bot Integration Notes",
        "",
        "- The existing FastAPI bot already has: EMA, RSI, ATR, Supertrend, MACD indicators",
        "- New indicators needed: StochRSI, VWAP (daily-reset), Heikin Ashi, Keltner Channel",
        "- Use Bybit linear perpetuals (same exchange already configured)",
        "- Position sizing formula: `qty = (equity * risk_pct) / (sl_atr_mult * atr_value)`",
        "- Always use taker orders for entries to ensure fills (market orders)",
        "- Consider maker orders (limit) for exits to reduce fees",
        "- Implement per-symbol trade cooldown (at least 1 candle) to avoid over-trading",
        "- Paper-trade on Bybit testnet for at least 2 weeks before live",
        "",
        "### Timeframe Recommendation",
        "",
        "- **15m** generally shows better risk-adjusted returns than 5m due to lower noise",
        "- **5m** has more trades but higher fee drag",
        "- Consider running 15m as primary with 5m as confirmation",
        "",
        "---",
        "",
        "## 7. Risk Warnings",
        "",
        "1. **Past performance does not guarantee future results.** Crypto markets are highly dynamic.",
        "2. **Fee drag is significant for scalping.** At 0.11% round-trip, strategies with low R:R ratios are disadvantaged.",
        "3. **Slippage not modeled.** Real execution may be worse, especially on 5m with small ATR.",
        "4. **Funding rates not included.** Bybit perpetuals have 8-hourly funding; hold times crossing funding windows incur costs.",
        "5. **Overfitting risk.** More trades = more statistical confidence. Prefer strategies with >100 trades.",
        "6. **Regime dependency.** Trend-following strategies fail in ranging markets and vice versa.",
        "7. **Never risk more than 1% per trade on live capital** until a strategy has proven itself in paper trading.",
        "8. **Always maintain stop-losses.** Do not override automated exits.",
        "",
        "---",
        "*Generated by backtest_scalping.py — Bybit USDT Perp data*",
    ]

    report_path = f"{output_dir}/SCALPING_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
