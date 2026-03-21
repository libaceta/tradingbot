"""
Portfolio-level risk guards (circuit breakers).
Halts trading if daily drawdown or position limits are exceeded.
"""
from datetime import datetime, timezone, timedelta

from bot.config.settings import settings
from bot.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioGuard:
    """
    Checks portfolio-level risk conditions before allowing new trades.
    """

    def __init__(self) -> None:
        self._day_start_equity: float = 0.0
        self._day_start_time: datetime = datetime.now(timezone.utc)
        self._halted: bool = False
        self._halt_reason: str = ""
        self._open_positions: int = 0

    def initialize(self, equity: float) -> None:
        """Call at bot start with current equity."""
        self._day_start_equity = equity
        self._day_start_time = datetime.now(timezone.utc)
        logger.info("portfolio_guard_initialized", equity=equity)

    def update_positions(self, count: int) -> None:
        self._open_positions = count

    def reset_daily(self, equity: float) -> None:
        """Call at midnight UTC to reset daily P&L tracking."""
        self._day_start_equity = equity
        self._day_start_time = datetime.now(timezone.utc)
        self._halted = False
        self._halt_reason = ""
        logger.info("portfolio_guard_daily_reset", equity=equity)

    def can_trade(self, current_equity: float) -> tuple[bool, str]:
        """
        Returns (can_trade, reason_if_not).
        Checks:
        1. Max open positions
        2. Daily loss circuit breaker
        3. Manual halt
        """
        if self._halted:
            return False, f"HALTED: {self._halt_reason}"

        # Reset daily if new UTC day
        now = datetime.now(timezone.utc)
        if (now - self._day_start_time) > timedelta(hours=24):
            self.reset_daily(current_equity)

        # Max open positions
        if self._open_positions >= settings.max_open_positions:
            return False, f"MAX_POSITIONS: {self._open_positions}/{settings.max_open_positions}"

        # Daily loss circuit breaker
        if self._day_start_equity > 0:
            daily_loss_pct = (self._day_start_equity - current_equity) / self._day_start_equity
            if daily_loss_pct >= settings.max_daily_loss_pct:
                self._halted = True
                self._halt_reason = (
                    f"DAILY_LOSS_LIMIT: {daily_loss_pct:.2%} >= "
                    f"{settings.max_daily_loss_pct:.2%}"
                )
                logger.critical(
                    "daily_loss_circuit_breaker_triggered",
                    daily_loss_pct=daily_loss_pct,
                    equity=current_equity,
                    day_start_equity=self._day_start_equity,
                )
                return False, self._halt_reason

        return True, ""

    def halt(self, reason: str = "MANUAL") -> None:
        self._halted = True
        self._halt_reason = reason
        logger.warning("portfolio_guard_halted", reason=reason)

    def resume(self) -> None:
        self._halted = False
        self._halt_reason = ""
        logger.info("portfolio_guard_resumed")

    @property
    def is_halted(self) -> bool:
        return self._halted

    @property
    def halt_reason(self) -> str:
        return self._halt_reason
