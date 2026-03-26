from __future__ import annotations

from dataclasses import dataclass

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


@dataclass
class BrokerPosition:
    qty: float
    avg_entry_price: float


class AlpacaBroker:
    def __init__(self, api_key: str, api_secret: str, paper: bool = True) -> None:
        self.client = TradingClient(api_key, api_secret, paper=paper)

    def get_position(self, symbol: str) -> BrokerPosition | None:
        try:
            p = self.client.get_open_position(symbol)
            return BrokerPosition(qty=float(p.qty), avg_entry_price=float(p.avg_entry_price))
        except Exception:
            return None

    def submit_market_buy_notional(self, symbol: str, notional_usd: float) -> None:
        if notional_usd <= 0:
            raise ValueError("notional_usd must be positive")

        req = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional_usd, 2),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
        )
        self.client.submit_order(req)

    def submit_market_sell_qty(self, symbol: str, qty: float) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")

        req = MarketOrderRequest(
            symbol=symbol,
            qty=round(qty, 6),
            side=OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        self.client.submit_order(req)
