"""
Base interfaces for trading strategies.

All strategies should implement this interface so they can plug into any
backtester or the live trading bot with minimal glue code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd


class BaseStrategy(ABC):
    """Strategy interface intentionally kept minimal and ergonomic."""

    @abstractmethod
    def process_klines(self, klines: List[List[Any]]) -> Optional[pd.DataFrame]:
        """Convert raw klines into a typed DataFrame with at least:
        columns: ['timestamp','open','high','low','close','volume']
        """

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Add indicator columns required by generate_signal."""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return signal dict with fields:
        - signal: 'BUY' | 'SELL' | 'HOLD'
        - confidence: int (0-100)
        - reasons: List[str]
        - risk: Optional dict with keys like: stop_loss, take_profit, atr
        """

    def analyze(self, klines: List[List[Any]]) -> Dict[str, Any]:
        """Convenience: end-to-end analysis."""
        df = self.process_klines(klines)
        if df is None:
            return {"signal": "HOLD", "confidence": 0, "reasons": ["Data processing failed"]}
        df = self.calculate_indicators(df)
        if df is None:
            return {"signal": "HOLD", "confidence": 0, "reasons": ["Indicator calculation failed"]}
        return self.generate_signal(df)


