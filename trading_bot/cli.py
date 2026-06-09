#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Trading Bot.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2500

# Stop-Market BUY (bonus order type)
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 68000

# Use environment variables for keys (recommended)
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from bot import (
    BinanceFuturesClient,
    place_order,
    format_order_summary,
    format_order_result,
    validate_all,
    setup_logging,
    get_logger,
)

# ---------------------------------------------------------------------------
# Logging — must be set up before any other bot imports use the logger
# ---------------------------------------------------------------------------
setup_logging(log_level="WARNING")   # console: WARNING+; file: DEBUG
logger = get_logger("cli")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot\n"
            "Place MARKET, LIMIT, or STOP_MARKET orders via the command line."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Credentials are read from --api-key / --api-secret flags or from\n"
            "the environment variables BINANCE_API_KEY and BINANCE_API_SECRET.\n\n"
            "Examples:\n"
            "  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001\n"
            "  python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2500\n"
            "  python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 68000\n"
        ),
    )

    # --- Credentials ---
    creds = parser.add_argument_group("API credentials (or use env vars)")
    creds.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY", ""),
        help="Binance API key (env: BINANCE_API_KEY)",
    )
    creds.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET", ""),
        help="Binance API secret (env: BINANCE_API_SECRET)",
    )

    # --- Order parameters ---
    order = parser.add_argument_group("Order parameters")
    order.add_argument(
        "--symbol", required=True, help="Trading pair, e.g. BTCUSDT"
    )
    order.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], help="BUY or SELL"
    )
    order.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        help="Order type",
    )
    order.add_argument(
        "--quantity", required=True, help="Order quantity in base asset"
    )
    order.add_argument(
        "--price", default=None, help="Limit price (required for LIMIT orders)"
    )
    order.add_argument(
        "--stop-price",
        dest="stop_price",
        default=None,
        help="Stop trigger price (required for STOP_MARKET orders)",
    )
    order.add_argument(
        "--time-in-force",
        dest="time_in_force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )
    order.add_argument(
        "--reduce-only",
        dest="reduce_only",
        action="store_true",
        help="Mark order as reduce-only",
    )

    # --- Misc ---
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print summary without sending the order",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (file always logs DEBUG). Default: WARNING",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Reconfigure console log level if explicitly set
    if args.log_level != "WARNING":
        setup_logging(log_level=args.log_level)

    logger.info("CLI invoked with args: %s", vars(args))

    # --- Validate inputs ---
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
    except ValueError as exc:
        print(f"\n  ✗ Validation error: {exc}\n", file=sys.stderr)
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    # Validate stop_price separately (only for STOP_MARKET)
    stop_price: Decimal | None = None
    if args.order_type == "STOP_MARKET":
        if args.stop_price is None:
            print(
                "\n  ✗ Validation error: --stop-price is required for STOP_MARKET orders.\n",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            from bot.validators import validate_quantity
            stop_price = validate_quantity(args.stop_price)  # reuse positive-number check
        except ValueError as exc:
            print(f"\n  ✗ Validation error (stop-price): {exc}\n", file=sys.stderr)
            sys.exit(1)

    # --- Print request summary ---
    print(
        format_order_summary(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=stop_price,
        )
    )

    if args.dry_run:
        print("  ℹ Dry-run mode — order NOT sent.\n")
        sys.exit(0)

    # --- Credential check ---
    if not args.api_key or not args.api_secret:
        print(
            "\n  ✗ API credentials missing.\n"
            "  Set --api-key / --api-secret or export BINANCE_API_KEY / BINANCE_API_SECRET.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Build client & place order ---
    client = BinanceFuturesClient(api_key=args.api_key, api_secret=args.api_secret)

    print("  Sending order to Binance Futures Testnet …\n")

    result = place_order(
        client=client,
        symbol=params["symbol"],
        side=params["side"],
        order_type=params["order_type"],
        quantity=params["quantity"],
        price=params["price"],
        stop_price=stop_price,
        time_in_force=args.time_in_force,
        reduce_only=args.reduce_only,
    )

    print(format_order_result(result))

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
