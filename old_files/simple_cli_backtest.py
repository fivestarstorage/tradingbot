"""
CLI for the unified backtester with the simplified EMA+RSI+ATR strategy.
Usage examples:
  python simple_cli_backtest.py --symbol BTCUSDT --interval 5m --limit 500
  python simple_cli_backtest.py --csv data/BTCUSDT_5m.csv
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

from simplified_strategy import SimplifiedEmaRsiAtrStrategy
from unified_backtester import UnifiedBacktester

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Backtester (Simplified Strategy)")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Trading pair symbol")
    parser.add_argument("--interval", type=str, default="5m", help="Kline interval (e.g., 1m,5m,15m,1h)")
    parser.add_argument("--limit", type=int, default=500, help="Number of klines to fetch (<=1000)")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV with columns: timestamp,open,high,low,close,volume")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital in quote currency")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission rate (e.g., 0.001 for 0.1%)")
    parser.add_argument("--min_conf", type=int, default=55, help="Minimum confidence for entries/exits")

    args = parser.parse_args()

    strategy = SimplifiedEmaRsiAtrStrategy()
    backtester = UnifiedBacktester(strategy=strategy, initial_capital=args.capital, commission=args.commission)

    if args.csv:
        klines = backtester.load_csv(args.csv)
    else:
        klines = backtester.fetch_klines(args.symbol, args.interval, args.limit)
        if not klines:
            raise SystemExit("Failed to fetch klines and no CSV provided.")

    results = backtester.run(klines, min_confidence=args.min_conf)

    print("\n" + "=" * 70)
    print("UNIFIED BACKTEST RESULTS")
    print("=" * 70)
    print(f"Initial Capital:      ${args.capital:.2f}")
    print(f"Final Equity:         ${results.final_equity:.2f}")
    print(f"Total Return:         {results.total_return:+.2f}%")
    print(f"Total P&L:            ${results.total_pnl:+.2f}")
    print()
    print(f"Total Trades:         {results.total_trades}")
    print(f"Winning Trades:       {results.winning_trades} ({results.win_rate:.1f}%)")
    print(f"Losing Trades:        {results.losing_trades}")
    print()
    print(f"Average Win:          {results.avg_win:+.2f}%")
    print(f"Average Loss:         {results.avg_loss:+.2f}%")
    print(f"Profit Factor:        {results.profit_factor:.2f}")
    print(f"Max Drawdown:         {results.max_drawdown:.2f}%")
    print(f"Sharpe Ratio:         {results.sharpe_ratio:.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()


