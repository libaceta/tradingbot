from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class SignalResult:
    direction: str  # "LONG" | "SHORT" | "NONE"
    ema_21: Optional[float] = None
    ema_55: Optional[float] = None
    ema_cross: Optional[bool] = None
    supertrend: Optional[float] = None
    supertrend_dir: Optional[str] = None
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    atr: Optional[float] = None
    close_price: Optional[float] = None
    skip_reason: Optional[str] = None


class BaseStrategy(ABC):
    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> SignalResult:
        """Evaluate the latest candle and return a signal."""
        ...
