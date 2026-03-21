import math
from decimal import Decimal, ROUND_DOWN


def round_down(value: float, decimals: int) -> float:
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def round_price(price: float, tick_size: float) -> float:
    if tick_size <= 0:
        return price
    decimals = max(0, -int(math.floor(math.log10(tick_size))))
    return round(round(price / tick_size) * tick_size, decimals)


def round_qty(qty: float, step_size: float) -> float:
    if step_size <= 0:
        return qty
    d_qty = Decimal(str(qty))
    d_step = Decimal(str(step_size))
    result = (d_qty / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step
    return float(result)


def pct_change(new_val: float, old_val: float) -> float:
    if old_val == 0:
        return 0.0
    return (new_val - old_val) / old_val * 100
