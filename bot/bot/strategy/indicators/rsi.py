"""Relative Strength Index — pure pandas implementation."""
import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI using Wilder's smoothing (EWM with alpha=1/period).
    Matches TradingView and most professional platforms.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))
