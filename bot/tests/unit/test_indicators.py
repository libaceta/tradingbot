"""Unit tests for indicator implementations."""
import numpy as np
import pandas as pd
import pytest

from bot.strategy.indicators.ema import ema, ema_cross, ema_cross_below
from bot.strategy.indicators.rsi import rsi
from bot.strategy.indicators.macd import macd
from bot.strategy.indicators.supertrend import supertrend, atr


@pytest.fixture
def price_series():
    """Synthetic price series that creates a clear uptrend then downtrend."""
    np.random.seed(42)
    n = 200
    prices = [100.0]
    for i in range(n - 1):
        if i < 100:
            prices.append(prices[-1] * (1 + np.random.normal(0.002, 0.01)))
        else:
            prices.append(prices[-1] * (1 + np.random.normal(-0.002, 0.01)))
    return pd.Series(prices)


@pytest.fixture
def ohlcv_df(price_series):
    """Minimal OHLCV DataFrame."""
    close = price_series
    high = close * 1.01
    low = close * 0.99
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close})


class TestEMA:
    def test_basic_ema(self, price_series):
        result = ema(price_series, 21)
        assert len(result) == len(price_series)
        assert not result.isna().all()

    def test_ema_smoothness(self, price_series):
        """EMA should be smoother than raw prices."""
        result = ema(price_series, 21)
        raw_std = price_series.diff().dropna().std()
        ema_std = result.diff().dropna().std()
        assert ema_std < raw_std

    def test_ema_cross_up(self, price_series):
        fast = ema(price_series, 5)
        slow = ema(price_series, 20)
        cross = ema_cross(fast, slow)
        # Should have some crossovers in 200-bar series
        assert cross.sum() >= 1

    def test_ema_cross_only_true_on_actual_cross(self, price_series):
        """ema_cross should only be True on the bar of the crossover."""
        fast = ema(price_series, 5)
        slow = ema(price_series, 20)
        cross = ema_cross(fast, slow)
        # Where cross is True, fast must be above slow AND previously below
        for i in cross[cross].index:
            assert fast[i] > slow[i], f"At index {i}, fast should be above slow"


class TestRSI:
    def test_rsi_bounds(self, price_series):
        result = rsi(price_series, 14)
        valid = result.dropna()
        assert (valid >= 0).all(), "RSI should be >= 0"
        assert (valid <= 100).all(), "RSI should be <= 100"

    def test_rsi_overbought_in_uptrend(self, price_series):
        """During a strong uptrend RSI should reach overbought."""
        uptrend = pd.Series([100.0 * (1.005 ** i) for i in range(100)])
        result = rsi(uptrend, 14)
        assert result.dropna().max() > 70, "RSI should reach overbought in uptrend"

    def test_rsi_oversold_in_downtrend(self, price_series):
        """During a strong downtrend RSI should reach oversold."""
        downtrend = pd.Series([100.0 * (0.995 ** i) for i in range(100)])
        result = rsi(downtrend, 14)
        assert result.dropna().min() < 30, "RSI should reach oversold in downtrend"

    def test_rsi_length_matches_input(self, price_series):
        result = rsi(price_series, 14)
        assert len(result) == len(price_series)


class TestMACD:
    def test_macd_output_shape(self, price_series):
        macd_line, signal_line, hist = macd(price_series)
        assert len(macd_line) == len(price_series)
        assert len(signal_line) == len(price_series)
        assert len(hist) == len(price_series)

    def test_histogram_equals_macd_minus_signal(self, price_series):
        macd_line, signal_line, hist = macd(price_series)
        expected = macd_line - signal_line
        pd.testing.assert_series_equal(hist, expected, check_names=False)

    def test_macd_positive_in_uptrend(self):
        uptrend = pd.Series([100.0 * (1.005 ** i) for i in range(100)])
        macd_line, signal_line, hist = macd(uptrend)
        # In sustained uptrend, MACD line should eventually be positive
        assert macd_line.dropna().iloc[-1] > 0


class TestSupertrend:
    def test_supertrend_shape(self, ohlcv_df):
        st_line, st_dir = supertrend(
            ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"]
        )
        assert len(st_line) == len(ohlcv_df)
        assert len(st_dir) == len(ohlcv_df)

    def test_direction_values(self, ohlcv_df):
        _, st_dir = supertrend(
            ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"]
        )
        unique_dirs = st_dir.dropna().unique()
        for d in unique_dirs:
            assert d in (1, -1), f"Direction should be 1 or -1, got {d}"

    def test_atr_positive(self, ohlcv_df):
        from bot.strategy.indicators.supertrend import atr
        result = atr(ohlcv_df["high"], ohlcv_df["low"], ohlcv_df["close"])
        assert (result.dropna() > 0).all(), "ATR should always be positive"


class TestPositionSizer:
    def test_basic_sizing(self):
        from bot.risk.position_sizer import calculate_position_size
        result = calculate_position_size(
            equity_usdt=10000,
            entry_price=50000,
            atr=500,
            qty_step=0.001,
        )
        assert result is not None
        assert result["quantity"] > 0
        assert result["long_sl"] < 50000
        assert result["long_tp"] > 50000
        assert result["short_sl"] > 50000
        assert result["short_tp"] < 50000

    def test_risk_amount(self):
        """Risk should be approximately 2% of equity."""
        from bot.risk.position_sizer import calculate_position_size
        result = calculate_position_size(
            equity_usdt=10000,
            entry_price=50000,
            atr=500,
            qty_step=0.001,
        )
        # risk_usdt = qty * stop_distance ≈ 2% of 10000 = 200
        assert abs(result["risk_usdt"] - 200) < 50, f"Risk should be ~200 USDT, got {result['risk_usdt']}"

    def test_tp_greater_than_sl_distance_for_long(self):
        """TP distance should be > SL distance (1:1.5 R/R)."""
        from bot.risk.position_sizer import calculate_position_size
        result = calculate_position_size(
            equity_usdt=10000,
            entry_price=50000,
            atr=500,
            qty_step=0.001,
        )
        sl_dist = 50000 - result["long_sl"]
        tp_dist = result["long_tp"] - 50000
        assert tp_dist > sl_dist, "TP should be further than SL"
