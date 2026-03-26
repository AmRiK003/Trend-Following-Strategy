from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BrokerPosition:
    qty: float
    avg_entry_price: float


class PaperBroker:
    def __init__(self, state_file: str, trades_file: str, starting_cash: float = 100000.0) -> None:
        self.state_path = Path(state_file)
        self.trades_path = Path(trades_file)
        self.starting_cash = float(starting_cash)
        self._ensure_state()
        self._ensure_trades_csv()

    def _ensure_state(self) -> None:
        if self.state_path.exists():
            return
        state = {"cash": self.starting_cash, "positions": {}}
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _load_state(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _ensure_trades_csv(self) -> None:
        if self.trades_path.exists():
            return
        with self.trades_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "symbol", "side", "qty", "price", "notional", "cash_after"])

    def _log_trade(self, symbol: str, side: str, qty: float, price: float, notional: float, cash_after: float) -> None:
        with self.trades_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    symbol,
                    side,
                    f"{qty:.8f}",
                    f"{price:.4f}",
                    f"{notional:.2f}",
                    f"{cash_after:.2f}",
                ]
            )

    def get_position(self, symbol: str) -> BrokerPosition | None:
        state = self._load_state()
        p = state["positions"].get(symbol, {})
        qty = float(p.get("qty", 0.0))
        if qty <= 0:
            return None
        return BrokerPosition(qty=qty, avg_entry_price=float(p.get("avg_entry_price", 0.0)))

    def get_cash(self) -> float:
        state = self._load_state()
        return float(state["cash"])

    def submit_market_buy_notional(self, symbol: str, notional_usd: float, fill_price: float) -> None:
        if notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        if fill_price <= 0:
            raise ValueError("fill_price must be positive")

        state = self._load_state()
        cash = float(state["cash"])
        spend = min(float(notional_usd), cash)
        if spend <= 0:
            raise ValueError("No cash available for buy.")

        qty = spend / fill_price
        pos = state["positions"].get(symbol, {"qty": 0.0, "avg_entry_price": 0.0})
        old_qty = float(pos["qty"])
        old_avg = float(pos["avg_entry_price"])
        new_qty = old_qty + qty
        new_avg = ((old_qty * old_avg) + spend) / new_qty
        pos["qty"] = new_qty
        pos["avg_entry_price"] = new_avg
        state["positions"][symbol] = pos
        state["cash"] = cash - spend
        self._save_state(state)
        self._log_trade(symbol, "BUY", qty, fill_price, spend, float(state["cash"]))

    def submit_market_sell_qty(self, symbol: str, qty: float, fill_price: float) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if fill_price <= 0:
            raise ValueError("fill_price must be positive")

        state = self._load_state()
        pos = state["positions"].get(symbol, {"qty": 0.0, "avg_entry_price": 0.0})
        held = float(pos["qty"])
        if held <= 0:
            raise ValueError("No position to sell.")

        sell_qty = min(float(qty), held)
        proceeds = sell_qty * fill_price
        remaining = held - sell_qty

        if remaining <= 0:
            state["positions"].pop(symbol, None)
        else:
            pos["qty"] = remaining
            state["positions"][symbol] = pos

        state["cash"] = float(state["cash"]) + proceeds
        self._save_state(state)
        self._log_trade(symbol, "SELL", sell_qty, fill_price, proceeds, float(state["cash"]))
