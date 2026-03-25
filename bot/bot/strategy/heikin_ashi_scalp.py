"""
Heikin Ashi + EMA21 + EMA200 Scalping Strategy.

Optimized for ETHUSDT on 15-minute candles based on 180-day backtest
results across 10 professional scalping strategies.

Entry conditions:
  LONG:
    1. HA candle just turned bullish (color change: bearish → bullish)
    2. HA close is above EMA21 (short-term trend filter)
    3. Close price is above EMA200 (macro trend filter — only long in uptrend)
    4. ATR is above minimum threshold (avoid flat markets)
    5. Not in cooldown period after last exit

  SHORT:
    1. HA candle just turned bearish (color change: bullish → bearish)
    2. HA close is below EMA21 (short-term trend filter)
    3. Close price is below EMA200 (macro trend filter — only short in downtrend)
    4. ATR is above minimum threshold
    5. Not in cooldown period after last exit

Exit conditions:
  LONG exit:  HA candle turns bearish OR RSI > overbought
  SHORT exit: HA candle turns bullish  OR RSI < oversold

SL/TP: ATR-based, handled by exchange conditional orders.
  SL = 1.0x ATR, TP = 2.0x ATR (R:R = 1:2)
"""
from datetime import datetime, timezone
from typing import Optional

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

# Minimum candles needed for indicators to warm up (EMA200 needs the most)
MIN_CANDLES = max(
    settings.ha_ema_trend_period + 10,
    settings.ha_ema_period + 10,
    settings.rsi_period + 5,
    settings.supertrend_period + 5,
)


class HeikinAshiScalpStrategy(BaseStrategy):
    """
    Heikin Ashi + EMA21 + EMA200 scalping strategy.

    Key improvements over v1:
    - EMA200 macro trend filter: only LONG above EMA200, only SHORT below EMA200
    - Cooldown: N candles wait after any exit before re-entry
    - Tighter SL: 1×ATR instead of 2×ATR
    """

    def __init__(self) -> None:
        self.ema_period = settings.ha_ema_period
        self.ema_trend_period = settings.ha_ema_trend_period
        self.rsi_period = settings.rsi_period
        self.rsi_ob = settings.rsi_overbought
        self.rsi_os = settings.rsi_oversold
        self.atr_period = settings.supertrend_period
        self.atr_min_pct = settings.ha_atr_min_pct
        self.cooldown_candles = settings.ha_cooldown_candles
        self._last_exit_time: Optional[datetime] = None

    def record_exit(self, candle_time: datetime) -> None:
        """
        Called by main.py after any trade closes (win or loss).
        Activates the cooldown period to prevent immediate re-entry.
        """
        self._last_exit_time = candle_time

    def _in_cooldown(self, current_candle_time: datetime) -> bool:
        """Returns True if we're still within the cooldown window after the last exit."""
        if self._last_exit_time is None:
            return False
        interval_secs = settings.trade_interval * 60
        elapsed_secs = (current_candle_time - self._last_exit_time).total_seconds()
        candles_elapsed = elapsed_secs / interval_secs
        return candles_elapsed < self.cooldown_candles

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

        # Short-term trend filter
        df["ema21"] = ema(close, self.ema_period)

        # Macro trend filter — prevents trading against dominant trend
        df["ema200"] = ema(close, self.ema_trend_period)

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
        ema200_val = float(last["ema200"])
        rsi_val = float(last["rsi"])
        atr_val = float(last["atr"])
        bull_change = bool(last["ha_bull_change"])
        bear_change = bool(last["ha_bear_change"])

        base = SignalResult(
            direction="NONE",
            ema_21=ema21_val,
            ema_55=ema200_val,
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

        # ATR volatility filter: skip flat/low-volatility markets
        atr_pct = atr_val / close_price if close_price > 0 else 0
        if atr_pct < self.atr_min_pct:
            base.skip_reason = f"low_volatility(atr_pct={atr_pct:.4f}<{self.atr_min_pct})"
            return base

        # Cooldown filter: wait N candles after any exit
        candle_time = last.get("open_time")
        if candle_time is not None:
            # Ensure timezone-aware for comparison
            if hasattr(candle_time, "tzinfo") and candle_time.tzinfo is None:
                candle_time = candle_time.replace(tzinfo=timezone.utc)
            if self._in_cooldown(candle_time):
                base.skip_reason = f"cooldown({self.cooldown_candles}_candles_after_exit)"
                return base

        # ---- LONG entry ----
        # HA turned bullish + above EMA21 + above EMA200 (macro uptrend)
        if bull_change and ha_close_val > ema21_val and close_price > ema200_val:
            base.direction = "LONG"
            return base

        # ---- SHORT entry ----
        # HA turned bearish + below EMA21 + below EMA200 (macro downtrend)
        if bear_change and ha_close_val < ema21_val and close_price < ema200_val:
            base.direction = "SHORT"
            return base

        # Build skip reason
        reasons = []
        if not (bull_change or bear_change):
            reasons.append("no_ha_color_change")
        elif bull_change:
            if ha_close_val <= ema21_val:
                reasons.append("ha_bull_but_below_ema21")
            elif close_price <= ema200_val:
                reasons.append("ha_bull_but_below_ema200_downtrend")
        elif bear_change:
            if ha_close_val >= ema21_val:
                reasons.append("ha_bear_but_above_ema21")
            elif close_price >= ema200_val:
                reasons.append("ha_bear_but_above_ema200_uptrend")

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
