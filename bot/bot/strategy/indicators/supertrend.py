"""
Supertrend indicator — pure pandas/numpy implementation.
Formula based on ATR with upper/lower bands.
"""
from typing import Tuple
import numpy as np
import pandas as pd


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0,
) -> Tuple[pd.Series, pd.Series]:
    """
    Compute Supertrend indicator.

    Returns:
        (supertrend_line, direction)
        direction: +1 = bullish (price above supertrend), -1 = bearish
    """
    hl2 = (high + low) / 2
    atr_val = atr(high, low, close, period)

    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    n = len(close)
    st = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)  # 1 = up, -1 = down

    # Initialize
    final_upper = upper_band.values.copy()
    final_lower = lower_band.values.copy()

    for i in range(1, n):
        # Adjust bands
        if final_lower[i] > final_lower[i - 1] or close.iloc[i - 1] < final_lower[i - 1]:
            final_lower[i] = final_lower[i]
        else:
            final_lower[i] = final_lower[i - 1]

        if final_upper[i] < final_upper[i - 1] or close.iloc[i - 1] > final_upper[i - 1]:
            final_upper[i] = final_upper[i]
        else:
            final_upper[i] = final_upper[i - 1]

        # Direction
        if np.isnan(st[i - 1]):
            direction[i] = 1
            st[i] = final_lower[i]
        elif st[i - 1] == final_upper[i - 1]:
            if close.iloc[i] <= final_upper[i]:
                direction[i] = -1
                st[i] = final_upper[i]
            else:
                direction[i] = 1
                st[i] = final_lower[i]
        else:  # st was lower band (bullish)
            if close.iloc[i] >= final_lower[i]:
                direction[i] = 1
                st[i] = final_lower[i]
            else:
                direction[i] = -1
                st[i] = final_upper[i]

    st_series = pd.Series(st, index=close.index)
    dir_series = pd.Series(direction, index=close.index)

    return st_series, dir_series
