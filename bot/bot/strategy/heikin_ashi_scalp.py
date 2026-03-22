"""
Heikin Ashi + EMA21 Scalping Strategy.

Optimized for ETHUSDT on 15-minute candles based on 180-day backtest
results across 10 professional scalping strategies.

Entry conditions:
  LONG:
    1. HA candle just turned bullish (color change: bearish → bullish)
    2. HA close is above EMA21 (trend filter)
    3. ATR is above minimum threshold (avoid flat markets)

  SHORT:
    1. HA candle just turned bearish (color change: bullish → bearish)
    2. HA close is below EMA21 (trend filter)
    3. ATR is above minimum threshold

Exit conditions:
  LONG exit:  HA candle turns bearish OR RSI > overbought
  SHORT exit: HA candle turns bullish  OR RSI < oversold

SL/TP: ATR-based, handled by exchange conditional orders.
  Recommended: SL = 1.5x ATR, TP = 2.5x ATR (configurable via .env)
"""
import pandas as pd

from bot.config.settings import settings
from bot.strategy.base import BaseStrategy, SignalResult
from bot.strategy.indicators.ema import ema
from bot.strategy.indicators.rsi import rsi
from bot.strategy.indicators.supertrend import atr
from bot.strategy.indicators.heikin_ashi import (
    heikin_ashi,
    ha_is_bullish,
    ha_color_change_to_bull,
    ha_color_change_to_bear,
)

# Minimum candles needed for indicators to warm up
MIN_CANDLES = max(
    settings.ha_ema_period + 10,
    settings.rsi_period + 5,
    settings.supertrend_period + 5,
)


class HeikinAshiScalpStrategy(BaseStrategy):
    """
    Heikin Ashi + EMA21 scalping strategy.
    Trades momentum shifts identified by HA color changes filtered by EMA trend.
    """

    def __init__(self) -> None:
        self.ema_period = settings.ha_ema_period
        self.rsi_period = settings.rsi_period
        self.rsi_ob = settings.rsi_overbought
        self.rsi_os = settings.rsi_oversold
        self.atr_period = settings.supertrend_period
        self.atr_min_pct = settings.ha_atr_min_pct  # min ATR as % of price

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all indicators and attach to DataFrame."""
        df = df.copy()
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # Heikin Ashi candles
        ha = heikin_ashi(df)
        df["ha_open"] = ha["ha_open"]
        df["ha_high"] = ha["ha_high"]
        df["ha_low"] = ha["ha_low"]
        df["ha_close"] = ha["ha_close"]

        # Color change signals
        df["ha_bull_change"] = ha_color_change_to_bull(ha)
        df["ha_bear_change"] = ha_color_change_to_bear(ha)
        df["ha_bullish"] = ha_is_bullish(ha)

        # EMA trend filter
        df["ema21"] = ema(close, self.ema_period)

        # RSI for exit
        df["rsi"] = rsi(close, self.rsi_period)

        # ATR for volatility filter and position sizing
        df["atr"] = atr(high, low, close, self.atr_period)

        return df

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        """Evaluate the most recent candle and return a signal."""
        if len(df) < MIN_CANDLES:
            return SignalResult(
                direction="NONE",
                skip_reason=f"Not enough candles: {len(df)} < {MIN_CANDLES}",
            )

        df = self.compute_indicators(df)
        last = df.iloc[-1]

        close_price = float(last["close"])
        ha_close_val = float(last["ha_close"])
        ha_open_val = float(last["ha_open"])
        ema21_val = float(last["ema21"])
        rsi_val = float(last["rsi"])
        atr_val = float(last["atr"])
        bull_change = bool(last["ha_bull_change"])
        bear_change = bool(last["ha_bear_change"])

        # ATR volatility filter: skip flat/low-volatility markets
        atr_pct = atr_val / close_price if close_price > 0 else 0
        low_vol = atr_pct < self.atr_min_pct

        base = SignalResult(
            direction="NONE",
            ema_21=ema21_val,
            ema_55=None,
            ema_cross=bull_change or bear_change,
            supertrend=None,
            supertrend_dir="UP" if ha_close_val > ha_open_val else "DOWN",
            rsi=rsi_val,
            macd_line=None,
            macd_signal=None,
            macd_hist=None,
            atr=atr_val,
            close_price=close_price,
        )

        if low_vol:
            base.skip_reason = f"low_volatility(atr_pct={atr_pct:.4f}<{self.atr_min_pct})"
            return base

        # ---- LONG entry ----
        # HA just turned bullish AND close is above EMA21
        if bull_change and ha_close_val > ema21_val:
            base.direction = "LONG"
            return base

        # ---- SHORT entry ----
        # HA just turned bearish AND close is below EMA21
        if bear_change and ha_close_val < ema21_val:
            base.direction = "SHORT"
            return base

        # Build skip reason
        reasons = []
        if not (bull_change or bear_change):
            reasons.append("no_ha_color_change")
        elif bull_change and ha_close_val <= ema21_val:
            reasons.append("ha_bull_but_below_ema21")
        elif bear_change and ha_close_val >= ema21_val:
            reasons.append("ha_bear_but_above_ema21")

        base.skip_reason = ",".join(reasons) if reasons else "no_signal"
        return base

    def should_exit_long(
        self, df: pd.DataFrame, current_position: dict
    ) -> tuple[bool, str]:
        """
        Exit LONG when:
        - HA candle turns bearish (momentum shift)
        - RSI is overbought (exhaustion)
        SL/TP handled by exchange conditional orders.
        """
        df = self.compute_indicators(df)
        last = df.iloc[-1]

        bear_change = bool(last["ha_bear_change"])
        rsi_val = float(last["rsi"])

        if bear_change:
            return True, "HA_TURNED_BEARISH"
        if rsi_val > self.rsi_ob:
            return True, "RSI_OVERBOUGHT"
        return False, ""

    def should_exit_short(
        self, df: pd.DataFrame, current_position: dict
    ) -> tuple[bool, str]:
        """
        Exit SHORT when:
        - HA candle turns bullish (momentum shift)
        - RSI is oversold (exhaustion)
        SL/TP handled by exchange conditional orders.
        """
        df = self.compute_indicators(df)
        last = df.iloc[-1]

        bull_change = bool(last["ha_bull_change"])
        rsi_val = float(last["rsi"])

        if bull_change:
            return True, "HA_TURNED_BULLISH"
        if rsi_val < self.rsi_os:
            return True, "RSI_OVERSOLD"
        return False, ""
