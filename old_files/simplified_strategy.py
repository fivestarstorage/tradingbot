"""
Simplified EMA+RSI+ATR long-only strategy.

Design goals:
- Profitable bias in trending regimes with strong downside protection.
- Extremely simple parameters, easy to tune in .env or constructor.
- Deterministic, readable signals suitable for backtesting/live trading.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

from strategy_base import BaseStrategy


logger = logging.getLogger(__name__)


class SimplifiedEmaRsiAtrStrategy(BaseStrategy):
    """Long-only strategy using EMA trend, RSI pullback, and ATR risk controls.

    Entry (BUY):
      - Trend up: ema_fast > ema_slow
      - RSI pullback to neutral/oversold: rsi <= rsi_buy_max
      - Momentum resumption: close > ema_fast or rsi rising vs previous

    Exit (SELL):
      - Stop loss: 2x ATR below entry
      - Take profit: 3x ATR above entry (2:3 risk:reward)
      - Trend loss: ema_fast < ema_slow
    """

    def __init__(
        self,
        ema_fast: int = 20,
        ema_slow: int = 50,
        rsi_period: int = 14,
        rsi_buy_max: int = 45,
        atr_period: int = 14,
    ) -> None:
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_buy_max = rsi_buy_max
        self.atr_period = atr_period
        logger.info(
            f"Initialized SimplifiedEmaRsiAtrStrategy: EMA({ema_fast}/{ema_slow}), RSI({rsi_period})<= {rsi_buy_max}, ATR({atr_period})"
        )

    def process_klines(self, klines: List[List[Any]]) -> Optional[pd.DataFrame]:
        if not klines:
            logger.error("No kline data provided")
            return None
        df = pd.DataFrame(
            klines,
            columns=[
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "trades",
                "taker_buy_base",
                "taker_buy_quote",
                "ignore",
            ],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def calculate_indicators(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        if df is None or len(df) < max(self.ema_slow, self.atr_period, self.rsi_period) + 2:
            logger.error("Insufficient data for indicator calculation")
            return None
        close = df["close"]
        high = df["high"]
        low = df["low"]
        ema_fast_ind = EMAIndicator(close=close, window=self.ema_fast)
        ema_slow_ind = EMAIndicator(close=close, window=self.ema_slow)
        rsi_ind = RSIIndicator(close=close, window=self.rsi_period)
        atr_ind = AverageTrueRange(high=high, low=low, close=close, window=self.atr_period)

        df = df.copy()
        df["ema_fast"] = ema_fast_ind.ema_indicator()
        df["ema_slow"] = ema_slow_ind.ema_indicator()
        df["rsi"] = rsi_ind.rsi()
        df["atr"] = atr_ind.average_true_range()
        df["trend"] = np.where(df["ema_fast"] > df["ema_slow"], 1, -1)
        return df

    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or len(df) < 2:
            return {"signal": "HOLD", "confidence": 0, "reasons": ["Insufficient data"]}

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(latest["close"]) 
        ema_fast = float(latest["ema_fast"]) if not np.isnan(latest["ema_fast"]) else None
        ema_slow = float(latest["ema_slow"]) if not np.isnan(latest["ema_slow"]) else None
        rsi = float(latest["rsi"]) if not np.isnan(latest["rsi"]) else None
        atr = float(latest["atr"]) if not np.isnan(latest["atr"]) else None

        if any(v is None for v in [ema_fast, ema_slow, rsi, atr]):
            return {"signal": "HOLD", "confidence": 0, "reasons": ["Indicators not ready"]}

        signal = "HOLD"
        confidence = 0
        reasons: List[str] = []

        # BUY setup
        if ema_fast > ema_slow:
            reasons.append("Uptrend (EMA fast > slow)")
            if rsi <= self.rsi_buy_max:
                reasons.append(f"RSI pullback (RSI {rsi:.1f} <= {self.rsi_buy_max})")
                if price > ema_fast or latest["rsi"] > prev["rsi"]:
                    reasons.append("Momentum resumption confirmed")
                    signal = "BUY"
                    confidence = 65
        else:
            # Consider trend-loss exit if in position (handled by backtester/PM)
            reasons.append("Downtrend (EMA fast <= slow)")

        risk: Dict[str, Any] = {}
        if signal == "BUY":
            sl = price - 2.0 * atr
            tp = price + 3.0 * atr
            risk = {
                "stop_loss": float(sl),
                "take_profit": float(tp),
                "atr": float(atr),
            }

        result = {
            "signal": signal,
            "confidence": confidence,
            "reasons": reasons if reasons else ["No edge"],
            "indicators": {
                "price": price,
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "rsi": rsi,
                "atr": atr,
                "trend": 1 if ema_fast > ema_slow else -1,
            },
            "risk": risk,
        }
        logger.info(
            f"Signal: {result['signal']} (Conf {confidence}%) - "
            + ", ".join(result["reasons"][:3])
        )
        return result


