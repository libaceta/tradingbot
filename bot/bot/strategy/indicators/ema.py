"""Exponential Moving Average — pure pandas implementation."""
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Standard EMA using pandas ewm (consistent with most trading platforms).
    adjust=False matches the recursive formula: EMA_t = alpha*price + (1-alpha)*EMA_{t-1}
    where alpha = 2 / (period + 1)
    """
    return series.ewm(span=period, adjust=False).mean()


def ema_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """
    Returns True on the bar where fast crosses above slow (bullish crossover).
    """
    above = fast > slow
    return above & ~above.shift(1).fillna(False)


def ema_cross_below(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """
    Returns True on the bar where fast crosses below slow (bearish crossover).
    """
    below = fast < slow
    return below & ~below.shift(1).fillna(False)
