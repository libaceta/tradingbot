"""
Position sizing using the 2% risk-per-trade rule with ATR-based stop loss.

Formula:
  risk_amount = equity * risk_pct              (e.g. $10000 * 0.02 = $200)
  stop_distance = atr * atr_sl_multiplier      (e.g. 500 * 2.0 = $1000 per BTC)
  quantity = risk_amount / stop_distance       (e.g. $200 / $1000 = 0.2 BTC)
"""
from bot.config.settings import settings
from bot.utils.math_utils import round_qty
from bot.utils.logging import get_logger

logger = get_logger(__name__)


def calculate_position_size(
    equity_usdt: float,
    entry_price: float,
    atr: float,
    qty_step: float = 0.001,
    price_precision: int = 2,
) -> dict:
    """
    Calculate position size, stop loss, and take profit levels.

    Args:
        equity_usdt: Total account equity in USDT
        entry_price: Expected entry price
        atr: ATR value at entry
        qty_step: Minimum quantity increment for the symbol
        price_precision: Decimal places for price rounding

    Returns dict with:
        quantity, stop_loss_price, take_profit_price, risk_usdt,
        stop_distance, notional_usdt, sl_pct, tp_pct
    """
    risk_usdt = equity_usdt * settings.risk_per_trade
    stop_distance = atr * settings.atr_sl_multiplier
    tp_distance = atr * settings.atr_tp_multiplier

    if stop_distance <= 0:
        logger.warning("position_sizer_zero_atr", atr=atr)
        return {}

    quantity = risk_usdt / stop_distance
    quantity = round_qty(quantity, qty_step)

    # Enforce minimum order size
    notional = quantity * entry_price
    if notional < settings.min_order_usdt:
        logger.warning(
            "position_below_min_notional",
            notional=notional,
            min=settings.min_order_usdt,
        )
        quantity = round_qty(settings.min_order_usdt / entry_price, qty_step)
        notional = quantity * entry_price

    round_p = 10 ** price_precision

    return {
        "quantity": quantity,
        "risk_usdt": round(quantity * stop_distance, 4),
        "notional_usdt": round(notional, 4),
        "stop_distance": stop_distance,
        "tp_distance": tp_distance,
        # Long levels
        "long_sl": round(entry_price - stop_distance, price_precision),
        "long_tp": round(entry_price + tp_distance, price_precision),
        # Short levels
        "short_sl": round(entry_price + stop_distance, price_precision),
        "short_tp": round(entry_price - tp_distance, price_precision),
        "sl_pct": round(stop_distance / entry_price * 100, 3),
        "tp_pct": round(tp_distance / entry_price * 100, 3),
    }
