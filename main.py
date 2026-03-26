from __future__ import annotations

import argparse
import time
from datetime import datetime

from bot.broker import AlpacaBroker
from bot.config import load_settings
from bot.data import fetch_ohlcv
from bot.paper_broker import PaperBroker
from bot.strategy import StrategyConfig, generate_signal


def run_once(dry_run: bool = False) -> None:
    settings = load_settings()
    if settings.broker_mode == "alpaca":
        broker = AlpacaBroker(
            api_key=settings.alpaca_api_key or "",
            api_secret=settings.alpaca_api_secret or "",
            paper=settings.alpaca_paper,
        )
    else:
        broker = PaperBroker(
            state_file=settings.paper_state_file,
            trades_file=settings.paper_trades_file,
            starting_cash=settings.paper_starting_cash,
        )
    position = broker.get_position(settings.symbol)
    in_position = position is not None and position.qty > 0

    data = fetch_ohlcv(settings.symbol, period=settings.data_period, interval=settings.data_interval)
    cfg = StrategyConfig(
        breakout_lookback=settings.breakout_lookback,
        volume_lookback=settings.volume_lookback,
        volume_multiplier=settings.volume_multiplier,
        adx_period=settings.adx_period,
        adx_min=settings.adx_min,
        use_adx_filter=settings.use_adx_filter,
    )
    signal = generate_signal(data, cfg, in_position=in_position)

    price = float(data["Close"].iloc[-1])
    ts = datetime.now().isoformat(timespec="seconds")
    print(f"[{ts}] {settings.symbol} close={price:.2f} signal={signal} in_position={in_position}")

    if signal == "BUY" and not in_position:
        if dry_run:
            print(f"DRY RUN: would BUY {settings.symbol} with ${settings.position_size_usd:.2f}")
        else:
            if settings.broker_mode == "alpaca":
                broker.submit_market_buy_notional(settings.symbol, settings.position_size_usd)
                print(f"ORDER SENT: BUY {settings.symbol} notional ${settings.position_size_usd:.2f}")
            else:
                broker.submit_market_buy_notional(settings.symbol, settings.position_size_usd, price)
                print(f"PAPER EXECUTED: BUY {settings.symbol} notional ${settings.position_size_usd:.2f}")
    elif signal == "SELL" and in_position and position is not None:
        if dry_run:
            print(f"DRY RUN: would SELL {settings.symbol} qty={position.qty:.6f}")
        else:
            if settings.broker_mode == "alpaca":
                broker.submit_market_sell_qty(settings.symbol, position.qty)
                print(f"ORDER SENT: SELL {settings.symbol} qty={position.qty:.6f}")
            else:
                broker.submit_market_sell_qty(settings.symbol, position.qty, price)
                print(f"PAPER EXECUTED: SELL {settings.symbol} qty={position.qty:.6f}")
    else:
        print("No action.")

    if settings.broker_mode == "simulator":
        cash = broker.get_cash()
        print(f"SIM ACCOUNT: cash=${cash:.2f}")


def run_loop(dry_run: bool = False) -> None:
    settings = load_settings()
    print(
        f"Starting bot loop for {settings.symbol}. Polling every {settings.poll_seconds}s "
        f"(broker={settings.broker_mode}, paper={settings.alpaca_paper}, dry_run={dry_run})"
    )
    while True:
        try:
            run_once(dry_run=dry_run)
        except Exception as exc:
            print(f"Run error: {exc}")
        time.sleep(settings.poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trend-following breakout trading bot")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Do not place real orders")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.once:
        run_once(dry_run=args.dry_run)
    else:
        run_loop(dry_run=args.dry_run)
