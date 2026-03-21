"""
Professional trading performance metrics.
All functions accept pandas Series or numpy arrays.
"""
from typing import List, Optional
import numpy as np
import pandas as pd


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Sharpe ratio: (mean_return - risk_free) / std_return * sqrt(periods_per_year)"""
    if returns.std() == 0:
        return 0.0
    excess = returns.mean() - risk_free_rate / periods_per_year
    return float(excess / returns.std() * np.sqrt(periods_per_year))


def sortino_ratio(returns: pd.Series, target: float = 0.0, periods_per_year: int = 252) -> float:
    """Sortino ratio: uses only downside deviation."""
    downside = returns[returns < target]
    if len(downside) == 0 or downside.std() == 0:
        return 0.0
    excess = returns.mean() - target
    downside_std = np.sqrt(np.mean(downside ** 2))
    if downside_std == 0:
        return 0.0
    return float(excess / downside_std * np.sqrt(periods_per_year))


def max_drawdown(equity_curve: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a positive percentage."""
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return float(abs(drawdown.min()) * 100)


def calmar_ratio(total_return_pct: float, max_dd_pct: float) -> float:
    """Calmar = annualized_return / max_drawdown"""
    if max_dd_pct == 0:
        return 0.0
    return float(total_return_pct / max_dd_pct)


def profit_factor(net_pnls: List[float]) -> float:
    """Gross profit / gross loss."""
    gross_profit = sum(p for p in net_pnls if p > 0)
    gross_loss = abs(sum(p for p in net_pnls if p < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


def win_rate(net_pnls: List[float]) -> float:
    """Percentage of winning trades."""
    if not net_pnls:
        return 0.0
    wins = sum(1 for p in net_pnls if p > 0)
    return float(wins / len(net_pnls) * 100)


def avg_r_multiple(r_multiples: List[float]) -> float:
    if not r_multiples:
        return 0.0
    return float(np.mean(r_multiples))


def compute_equity_curve(
    initial_capital: float,
    net_pnls: List[float],
    entry_times: List,
) -> List[dict]:
    """Build equity curve as list of {time, value} dicts."""
    equity = initial_capital
    curve = [{"time": int(entry_times[0].timestamp() * 1000) if entry_times else 0, "value": equity}]
    for i, pnl in enumerate(net_pnls):
        equity += pnl
        ts = entry_times[i] if i < len(entry_times) else None
        if ts is not None:
            curve.append({
                "time": int(ts.timestamp() * 1000),
                "value": round(equity, 4),
            })
    return curve


def compute_monthly_returns(
    equity_curve: List[dict],
    initial_capital: float,
) -> dict:
    """Build monthly returns map {year-month: pct}."""
    if not equity_curve:
        return {}

    df = pd.DataFrame(equity_curve)
    df["dt"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df = df.set_index("dt").sort_index()

    # Resample to month-end equity
    monthly = df["value"].resample("ME").last().ffill()
    monthly_pct = monthly.pct_change() * 100
    monthly_pct.iloc[0] = (monthly.iloc[0] - initial_capital) / initial_capital * 100

    return {str(dt.strftime("%Y-%m")): round(float(v), 4) for dt, v in monthly_pct.items()}


def compute_all_metrics(
    initial_capital: float,
    final_equity: float,
    net_pnls: List[float],
    r_multiples: List[float],
    entry_times: List,
    exit_times: List,
    equity_curve_points: List[dict],
    periods_per_year: int = 365,
) -> dict:
    """Compute all professional metrics in one call."""
    n_trades = len(net_pnls)
    if n_trades == 0:
        return {"total_trades": 0, "win_rate": 0, "total_return": 0}

    n_wins = sum(1 for p in net_pnls if p > 0)
    n_losses = n_trades - n_wins

    total_return_pct = (final_equity - initial_capital) / initial_capital * 100

    # Annualized return
    if entry_times and exit_times:
        total_days = (max(exit_times) - min(entry_times)).days or 1
        years = total_days / 365
        ratio = final_equity / initial_capital if initial_capital > 0 else 0
        if years > 0 and ratio > 0:
            annualized_return = (ratio ** (1 / years) - 1) * 100
        else:
            # Total loss or negative equity — cap at -100%
            annualized_return = -100.0
    else:
        annualized_return = 0

    # Build equity series for ratio calculations
    equity_vals = pd.Series([p["value"] for p in equity_curve_points])
    daily_returns = equity_vals.pct_change().dropna()

    max_dd = max_drawdown(equity_vals) if len(equity_vals) > 1 else 0
    sharpe = sharpe_ratio(daily_returns, periods_per_year=periods_per_year)
    sortino = sortino_ratio(daily_returns, periods_per_year=periods_per_year)
    calmar = calmar_ratio(annualized_return, max_dd)
    pf = profit_factor(net_pnls)
    wr = win_rate(net_pnls)
    avg_r = avg_r_multiple(r_multiples) if r_multiples else 0

    avg_duration = 0
    if entry_times and exit_times:
        durations = [(e - s).total_seconds() for s, e in zip(entry_times, exit_times) if e and s]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0

    return {
        "total_trades": n_trades,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate": round(wr, 4),
        "total_return": round(total_return_pct, 4),
        "annualized_return": round(annualized_return, 4),
        "max_drawdown": round(max_dd, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "profit_factor": round(pf, 4),
        "avg_r_multiple": round(avg_r, 4),
        "avg_trade_duration_secs": avg_duration,
        "total_fees_usdt": round(sum(abs(p) * 0.002 for p in net_pnls), 4),
        "final_equity": round(final_equity, 4),
    }
