"""
CLI backtest runner.

Usage:
  # Full VectorBT optimization:
  python scripts/run_backtest.py --engine vectorbt --symbol BTCUSDT --optimize

  # Detailed Backtesting.py single run:
  python scripts/run_backtest.py --engine backtestingpy --symbol BTCUSDT \\
    --start 2022-01-01 --end 2024-12-31 --capital 10000
"""
import argparse
import asyncio
import sys
from datetime import date

sys.path.insert(0, "/app")

from bot.backtest.runner import run_backtest
from bot.backtest.vectorbt_engine import DEFAULT_PARAM_RANGES
from bot.config.settings import settings
from bot.db.repositories.backtest_repo import get_leaderboard, get_backtest_runs
from bot.db.engine import get_session
from bot.utils.logging import configure_logging


def print_leaderboard(results: list):
    print("\n" + "=" * 100)
    print(f"{'Rank':<5} {'EMA F':<7} {'EMA S':<7} {'ST Mult':<9} {'RSI OB':<8} "
          f"{'Sharpe':<9} {'Return%':<10} {'MaxDD%':<9} {'WinRate%':<10} {'Trades':<8}")
    print("=" * 100)
    for i, r in enumerate(results, 1):
        print(
            f"{i:<5} {r.get('ema_fast', r.get('ema_fast') or '-'):<7} "
            f"{r.get('ema_slow', r.get('ema_slow') or '-'):<7} "
            f"{r.get('st_multiplier', '-'):<9} "
            f"{r.get('rsi_ob', '-'):<8} "
            f"{(r.get('sharpe_ratio') or 0):<9.4f} "
            f"{(r.get('total_return') or 0):<10.2f} "
            f"{(r.get('max_drawdown') or 0):<9.2f} "
            f"{(r.get('win_rate') or 0):<10.2f} "
            f"{(r.get('total_trades') or 0):<8}"
        )
    print("=" * 100 + "\n")


async def main(args):
    configure_logging("INFO", "pretty")

    params = {
        "ema_fast": args.ema_fast,
        "ema_slow": args.ema_slow,
        "st_period": settings.supertrend_period,
        "st_multiplier": settings.supertrend_multiplier,
        "rsi_period": settings.rsi_period,
        "rsi_ob": settings.rsi_overbought,
        "rsi_os": settings.rsi_oversold,
        "rsi_entry_min": args.rsi_entry_min,
        "rsi_entry_max": args.rsi_entry_max,
        "macd_fast": settings.macd_fast,
        "macd_slow": settings.macd_slow,
        "macd_signal": settings.macd_signal_period,
        "atr_sl_mult": settings.atr_sl_multiplier,
        "atr_tp_mult": settings.atr_tp_multiplier,
        "risk_per_trade": settings.risk_per_trade,
        "short_only": 1 if args.short_only else 0,
        "no_rsi_filter": 1 if args.no_rsi_filter else 0,
        "regime_filter": 1 if args.regime_filter else 0,
        "max_drop_pct": args.max_drop_pct,
        "peak_lookback": args.peak_lookback,
        "futures_mode": 1 if args.futures else 0,
        "leverage": args.leverage,
        # trend_filter must be 1 to activate MA200d regime logic.
        # It's automatically enabled when --bidirectional or --trend-filter is used.
        "trend_filter": 1 if (args.bidirectional or args.trend_filter) else 0,
        "bidirectional": 1 if args.bidirectional else 0,
        "trend_ma_period": args.trend_ma_period,
        "st_trigger": 1 if args.st_trigger else 0,
    }

    run_id = await run_backtest(
        engine=args.engine,
        symbol=args.symbol,
        interval=str(args.interval),
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        params=params,
        initial_capital=args.capital,
        optimize=args.optimize,
        param_ranges=DEFAULT_PARAM_RANGES if args.optimize else None,
    )

    print(f"\nBacktest run ID: {run_id}")

    # Print leaderboard
    async with get_session() as session:
        top = await get_leaderboard(session, symbol=args.symbol, limit=20)
        if top:
            top_dicts = []
            for r in top:
                top_dicts.append({
                    "ema_fast": r.ema_fast,
                    "ema_slow": r.ema_slow,
                    "st_multiplier": float(r.st_multiplier) if r.st_multiplier else None,
                    "rsi_ob": float(r.rsi_ob) if r.rsi_ob else None,
                    "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio else 0,
                    "total_return": float(r.total_return) if r.total_return else 0,
                    "max_drawdown": float(r.max_drawdown) if r.max_drawdown else 0,
                    "win_rate": float(r.win_rate) if r.win_rate else 0,
                    "total_trades": r.total_trades or 0,
                })
            print(f"\nTop {len(top_dicts)} Parameter Combinations (Sorted by Sharpe Ratio):")
            print_leaderboard(top_dicts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading Bot Backtester")
    parser.add_argument("--engine", default="backtestingpy", choices=["vectorbt", "backtestingpy"])
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default=60, type=int)
    parser.add_argument("--start", default="2024-03-20")
    parser.add_argument("--end", default="2026-03-20")
    parser.add_argument("--capital", default=100000.0, type=float)
    parser.add_argument("--optimize", action="store_true", help="Run VectorBT grid search")
    parser.add_argument("--ema-fast", default=settings.ema_fast, type=int)
    parser.add_argument("--ema-slow", default=settings.ema_slow, type=int)
    parser.add_argument("--rsi-entry-min", default=settings.rsi_entry_min, type=float)
    parser.add_argument("--rsi-entry-max", default=settings.rsi_entry_max, type=float)
    parser.add_argument("--short-only", action="store_true", help="Only take SHORT trades")
    parser.add_argument("--no-rsi-filter", action="store_true", help="Remove RSI 40-60 entry filter")
    parser.add_argument("--regime-filter", action="store_true", help="Enable regime filter (no short after >X%% drop)")
    parser.add_argument("--max-drop-pct", default=0.25, type=float, help="Max drop from peak to allow SHORT (default 0.25)")
    parser.add_argument("--peak-lookback", default=200, type=int, help="Bars for rolling peak calculation (default 200)")
    parser.add_argument("--futures", action="store_true", help="Futures mode: micro-BTC units + leverage")
    parser.add_argument("--leverage", default=1, type=int, help="Futures leverage multiplier (default 1 = spot)")
    parser.add_argument("--trend-filter", action="store_true", help="Block SHORT in bull market (price > MA200d)")
    parser.add_argument("--bidirectional", action="store_true", help="LONG when price>MA200d, SHORT when price<MA200d")
    parser.add_argument("--trend-ma-period", default=4800, type=int, help="Long-term MA period in bars (default 4800 = 200d on 1h)")
    parser.add_argument("--st-trigger", action="store_true", help="Use Supertrend flip as entry trigger instead of EMA crossover")
    args = parser.parse_args()

    asyncio.run(main(args))
