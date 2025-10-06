"""
Unified backtester with public data support and CSV ingestion.

Key features:
- Works with any strategy implementing BaseStrategy.
- Fetches data via Binance if API keys are present, otherwise supports CSV input.
- Simple metrics: return, win-rate, profit-factor, max drawdown, Sharpe.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from strategy_base import BaseStrategy
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    final_equity: float


class UnifiedBacktester:
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 1000.0, commission: float = 0.001) -> None:
        self.strategy = strategy
        self.initial_capital = float(initial_capital)
        self.commission = float(commission)

        self.capital = float(initial_capital)
        self.position: Optional[Dict[str, Any]] = None
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

    def load_csv(self, path: str) -> List[List[Any]]:
        """Load klines from a CSV with columns: timestamp, open, high, low, close, volume."""
        df = pd.read_csv(path)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required.issubset(set(df.columns)):
            raise ValueError(f"CSV missing required columns: {required}")

        # Build klines in expected list-of-lists shape
        klines: List[List[Any]] = []
        for _, r in df.iterrows():
            klines.append([
                int(r["timestamp"]),
                str(r["open"]),
                str(r["high"]),
                str(r["low"]),
                str(r["close"]),
                str(r["volume"]),
                0, 0, 0, 0, 0, 0,
            ])
        return klines

    def fetch_klines(self, symbol: str, interval: str, limit: int) -> Optional[List[List[Any]]]:
        """Fetch klines via Binance if credentials are configured."""
        try:
            from binance_client import BinanceClient
            client = BinanceClient(
                api_key=Config.BINANCE_API_KEY,
                api_secret=Config.BINANCE_API_SECRET,
                testnet=Config.USE_TESTNET,
            )
            return client.get_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logger.warning(f"Falling back: cannot fetch klines via API: {e}")
            return None

    def run(self, klines: List[List[Any]], min_confidence: int = 50) -> BacktestResult:
        if not klines or len(klines) < 100:
            raise ValueError("Insufficient data for backtesting (need >= 100 klines)")

        df = self.strategy.process_klines(klines)
        df = self.strategy.calculate_indicators(df)
        if df is None:
            raise ValueError("Failed to prepare data for backtest")

        for i in range(len(df)):
            if i < 60:
                continue
            current = df.iloc[i]
            price = float(current["close"])  # execution price
            timestamp = current["timestamp"]

            signal = self.strategy.generate_signal(df.iloc[: i + 1])
            side = signal.get("signal", "HOLD")
            confidence = int(signal.get("confidence", 0))
            risk = signal.get("risk", {})

            if self.position is not None:
                should_exit = False
                reason = None
                # Fixed stop/take logic from the stored position
                entry_price = float(self.position["entry_price"]) 
                stop_loss = float(self.position.get("stop_loss", entry_price * 0.98))
                take_profit = float(self.position.get("take_profit", entry_price * 1.03))

                if price <= stop_loss:
                    should_exit = True
                    reason = "Stop Loss"
                elif price >= take_profit:
                    should_exit = True
                    reason = "Take Profit"
                elif side == "SELL" and confidence >= min_confidence:
                    should_exit = True
                    reason = "Sell Signal"
                elif current.get("ema_fast", entry_price) < current.get("ema_slow", entry_price):
                    # Trend-loss exit
                    should_exit = True
                    reason = "Trend Loss"

                if should_exit:
                    self._close(price, timestamp, reason)

            elif side == "BUY" and confidence >= min_confidence:
                position_value = self.capital * 0.95
                quantity = position_value / price
                stop_loss = float(risk.get("stop_loss", price * 0.98))
                take_profit = float(risk.get("take_profit", price * 1.03))
                self._open(price, timestamp, quantity, stop_loss, take_profit, signal)

            equity = self.capital
            if self.position is not None:
                equity += self.position["quantity"] * price
            self.equity_curve.append({"timestamp": timestamp, "equity": equity, "price": price})

        if self.position is not None:
            last_price = float(df.iloc[-1]["close"])
            last_time = df.iloc[-1]["timestamp"]
            self._close(last_price, last_time, "End")

        return self._results()

    def _open(self, price: float, timestamp: Any, quantity: float, stop_loss: float, take_profit: float, signal: Dict[str, Any]) -> None:
        cost = quantity * price
        commission_cost = cost * self.commission
        self.position = {
            "entry_price": price,
            "entry_time": timestamp,
            "quantity": quantity,
            "cost": cost + commission_cost,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signal": signal,
        }
        self.capital -= (cost + commission_cost)
        logger.info(f"OPEN BUY {quantity:.6f} @ {price:.2f} | SL {stop_loss:.2f} TP {take_profit:.2f}")

    def _close(self, price: float, timestamp: Any, reason: str) -> None:
        if self.position is None:
            return
        quantity = self.position["quantity"]
        proceeds = quantity * price
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost
        pnl = net_proceeds - self.position["cost"]
        pnl_percent = (pnl / self.position["cost"]) * 100
        self.capital += net_proceeds
        trade = {
            "entry_time": self.position["entry_time"],
            "exit_time": timestamp,
            "entry_price": self.position["entry_price"],
            "exit_price": price,
            "quantity": quantity,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "reason": reason,
        }
        self.trades.append(trade)
        logger.info(f"CLOSE SELL {quantity:.6f} @ {price:.2f} | P&L {pnl_percent:+.2f}% | {reason}")
        self.position = None

    def _results(self) -> BacktestResult:
        if not self.trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_return=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                final_equity=self.initial_capital,
            )

        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] <= 0]
        total_pnl = sum(t["pnl"] for t in self.trades)
        total_return = (total_pnl / self.initial_capital) * 100
        win_rate = len(wins) / len(self.trades) * 100 if self.trades else 0.0
        avg_win = float(np.mean([t["pnl_percent"] for t in wins])) if wins else 0.0
        avg_loss = float(np.mean([t["pnl_percent"] for t in losses])) if losses else 0.0
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        equity_values = [e["equity"] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0.0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak * 100
            if drawdown > max_dd:
                max_dd = float(drawdown)

        returns = [t["pnl_percent"] for t in self.trades]
        sharpe = float(np.mean(returns) / np.std(returns)) if len(returns) > 1 and np.std(returns) > 0 else 0.0

        final_equity = self.capital
        if self.position is not None:
            # Should not happen (positions closed at end), but guard anyway
            final_equity += self.position["quantity"] * self.position["entry_price"]

        return BacktestResult(
            total_trades=len(self.trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return=total_return,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=float(profit_factor),
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            final_equity=float(final_equity),
        )


