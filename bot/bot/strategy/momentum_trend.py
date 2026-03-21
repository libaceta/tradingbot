"""
Multi-Indicator Momentum + Trend Following Strategy.

Entry conditions (ALL must be true):
  LONG:
    1. EMA21 crosses above EMA55 (or is already above and a recent cross occurred)
    2. Supertrend direction is UP (bullish)
    3. RSI is between rsi_entry_min (40) and rsi_entry_max (60)
    4. MACD line > MACD signal line (bullish momentum)

  SHORT:
    1. EMA21 crosses below EMA55
    2. Supertrend direction is DOWN (bearish)
    3. RSI is between rsi_entry_min and rsi_entry_max
    4. MACD line < MACD signal line (bearish momentum)

Exit conditions (any one triggers exit):
  LONG exit:  RSI > rsi_overbought (70) OR Supertrend flips DOWN OR SL hit OR TP hit
  SHORT exit: RSI < rsi_oversold (30)  OR Supertrend flips UP   OR SL hit OR TP hit
"""
import pandas as pd

from bot.config.settings import settings
from bot.strategy.base import BaseStrategy, SignalResult
from bot.strategy.indicators.ema import ema, ema_cross, ema_cross_below
from bot.strategy.indicators.supertrend import supertrend, atr
from bot.strategy.indicators.rsi import rsi
from bot.strategy.indicators.macd import macd


# Minimum candles needed for all indicators to warm up
MIN_CANDLES = max(
    settings.ema_slow + 10,
    settings.supertrend_period + 5,
    settings.macd_slow + settings.macd_signal_period + 5,
    settings.rsi_period + 5,
)


class MomentumTrendStrategy(BaseStrategy):
    def __init__(self) -> None:
        self.ema_fast_period = settings.ema_fast
        self.ema_slow_period = settings.ema_slow
        self.st_period = settings.supertrend_period
        self.st_mult = settings.supertrend_multiplier
        self.rsi_period = settings.rsi_period
        self.rsi_ob = settings.rsi_overbought
        self.rsi_os = settings.rsi_oversold
        self.rsi_entry_min = settings.rsi_entry_min
        self.rsi_entry_max = settings.rsi_entry_max
        self.macd_fast = settings.macd_fast
        self.macd_slow = settings.macd_slow
        self.macd_sig = settings.macd_signal_period

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all indicators and attach to DataFrame."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        df = df.copy()
        df["ema_fast"] = ema(close, self.ema_fast_period)
        df["ema_slow"] = ema(close, self.ema_slow_period)
        df["ema_cross_up"] = ema_cross(df["ema_fast"], df["ema_slow"])
        df["ema_cross_down"] = ema_cross_below(df["ema_fast"], df["ema_slow"])

        st_line, st_dir = supertrend(high, low, close, self.st_period, self.st_mult)
        df["supertrend"] = st_line
        df["supertrend_dir"] = st_dir  # +1 = bullish, -1 = bearish

        df["rsi"] = rsi(close, self.rsi_period)

        macd_line, macd_signal, macd_hist = macd(
            close, self.macd_fast, self.macd_slow, self.macd_sig
        )
        df["macd_line"] = macd_line
        df["macd_signal"] = macd_signal
        df["macd_hist"] = macd_hist

        df["atr"] = atr(high, low, close, self.st_period)

        return df

    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        """Evaluate the most recent candle after computing indicators."""
        if len(df) < MIN_CANDLES:
            return SignalResult(
                direction="NONE",
                skip_reason=f"Not enough candles: {len(df)} < {MIN_CANDLES}",
            )

        df = self.compute_indicators(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]

        close_price = float(last["close"])
        ema_fast_val = float(last["ema_fast"])
        ema_slow_val = float(last["ema_slow"])
        st_val = float(last["supertrend"])
        st_dir_val = int(last["supertrend_dir"])
        rsi_val = float(last["rsi"])
        macd_l = float(last["macd_line"])
        macd_s = float(last["macd_signal"])
        macd_h = float(last["macd_hist"])
        atr_val = float(last["atr"])
        cross_up = bool(last["ema_cross_up"])
        cross_down = bool(last["ema_cross_down"])

        # A "recent" cross: current or previous candle
        recent_cross_up = cross_up or bool(prev["ema_cross_up"])
        recent_cross_down = cross_down or bool(prev["ema_cross_down"])

        base = SignalResult(
            direction="NONE",
            ema_21=ema_fast_val,
            ema_55=ema_slow_val,
            ema_cross=cross_up or cross_down,
            supertrend=st_val,
            supertrend_dir="UP" if st_dir_val == 1 else "DOWN",
            rsi=rsi_val,
            macd_line=macd_l,
            macd_signal=macd_s,
            macd_hist=macd_h,
            atr=atr_val,
            close_price=close_price,
        )

        # ---- LONG entry ----
        if (
            recent_cross_up
            and ema_fast_val > ema_slow_val
            and st_dir_val == 1
            and self.rsi_entry_min <= rsi_val <= self.rsi_entry_max
            and macd_l > macd_s
        ):
            base.direction = "LONG"
            return base

        # ---- SHORT entry ----
        if (
            recent_cross_down
            and ema_fast_val < ema_slow_val
            and st_dir_val == -1
            and self.rsi_entry_min <= rsi_val <= self.rsi_entry_max
            and macd_l < macd_s
        ):
            base.direction = "SHORT"
            return base

        # Build skip reason for logging
        reasons = []
        if not (recent_cross_up or recent_cross_down):
            reasons.append("no_ema_cross")
        if st_dir_val == 1 and ema_fast_val <= ema_slow_val:
            reasons.append("ema_not_aligned")
        if not (self.rsi_entry_min <= rsi_val <= self.rsi_entry_max):
            reasons.append(f"rsi_out_of_range({rsi_val:.1f})")
        if abs(macd_l - macd_s) < 0.001 * close_price:
            reasons.append("macd_flat")

        base.skip_reason = ",".join(reasons) if reasons else "no_signal"
        return base

    def should_exit_long(self, df: pd.DataFrame, current_position: dict) -> tuple[bool, str]:
        """
        Check if a LONG position should be exited based on indicator conditions.
        Returns (should_exit, reason)
        SL/TP exits are handled by the exchange via conditional orders.
        """
        df = self.compute_indicators(df)
        last = df.iloc[-1]

        rsi_val = float(last["rsi"])
        st_dir = int(last["supertrend_dir"])

        if rsi_val > self.rsi_ob:
            return True, "RSI_OVERBOUGHT"
        if st_dir == -1:
            return True, "SUPERTREND_FLIP"
        return False, ""

    def should_exit_short(self, df: pd.DataFrame, current_position: dict) -> tuple[bool, str]:
        """
        Check if a SHORT position should be exited based on indicator conditions.
        Returns (should_exit, reason)
        """
        df = self.compute_indicators(df)
        last = df.iloc[-1]

        rsi_val = float(last["rsi"])
        st_dir = int(last["supertrend_dir"])

        if rsi_val < self.rsi_os:
            return True, "RSI_OVERSOLD"
        if st_dir == 1:
            return True, "SUPERTREND_FLIP"
        return False, ""
