"""
Heikin Ashi candle calculation.

Heikin Ashi smooths price action by averaging OHLC values, making trends
and reversals easier to spot than with standard candles.

Formulas:
  HA_close = (open + high + low + close) / 4
  HA_open  = (prev_HA_open + prev_HA_close) / 2  (iterative)
  HA_high  = max(high, HA_open, HA_close)
  HA_low   = min(low,  HA_open, HA_close)
"""
import pandas as pd


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Heikin Ashi candles from a standard OHLCV DataFrame.

    Args:
        df: DataFrame with columns [open, high, low, close]

    Returns:
        DataFrame with columns [ha_open, ha_high, ha_low, ha_close]
        indexed the same as input.
    """
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

    # HA open must be computed iteratively for accuracy
    ha_open_vals = [0.0] * len(df)
    ha_open_vals[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
    ha_close_arr = ha_close.to_numpy()
    for i in range(1, len(df)):
        ha_open_vals[i] = (ha_open_vals[i - 1] + ha_close_arr[i - 1]) / 2

    ha_open = pd.Series(ha_open_vals, index=df.index)

    ha_high = pd.concat([df["high"], ha_open, ha_close], axis=1).max(axis=1)
    ha_low = pd.concat([df["low"], ha_open, ha_close], axis=1).min(axis=1)

    return pd.DataFrame(
        {
            "ha_open": ha_open,
            "ha_high": ha_high,
            "ha_low": ha_low,
            "ha_close": ha_close,
        },
        index=df.index,
    )


def ha_is_bullish(ha: pd.DataFrame) -> pd.Series:
    """True when HA candle is bullish (close >= open)."""
    return ha["ha_close"] >= ha["ha_open"]


def ha_color_change_to_bull(ha: pd.DataFrame) -> pd.Series:
    """True on the first bullish HA candle after a bearish one."""
    bull = ha_is_bullish(ha)
    prev_bull = bull.shift(1).astype("boolean").fillna(True).astype(bool)
    return bull & ~prev_bull


def ha_color_change_to_bear(ha: pd.DataFrame) -> pd.Series:
    """True on the first bearish HA candle after a bullish one."""
    bear = ~ha_is_bullish(ha)
    prev_bear = bear.shift(1).astype("boolean").fillna(True).astype(bool)
    return bear & ~prev_bear
