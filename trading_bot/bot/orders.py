"""
Order placement logic.

This module sits between the CLI layer and the raw Binance client.
It handles:
- Building clean order summaries for display
- Logging each order attempt and result
- Returning a structured OrderResult for the CLI to render
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .client import BinanceFuturesClient, BinanceAPIError
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: int | None = None
    client_order_id: str | None = None
    symbol: str = ""
    side: str = ""
    order_type: str = ""
    orig_qty: str = ""
    executed_qty: str = ""
    avg_price: str = ""
    status: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None = None,
    stop_price: Decimal | None = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
) -> OrderResult:
    """
    Place an order via *client* and return a structured OrderResult.

    Never raises — all exceptions are caught and recorded in OrderResult.error.
    """
    logger.info(
        "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
        symbol,
        side,
        order_type,
        quantity,
        price if price is not None else "N/A",
    )

    try:
        raw = client.new_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed — BinanceAPIError: %s", exc)
        return OrderResult(success=False, error=str(exc))
    except Exception as exc:  # network errors, etc.
        logger.error("Order failed — unexpected error: %s", exc)
        return OrderResult(success=False, error=str(exc))

    result = OrderResult(
        success=True,
        order_id=raw.get("orderId"),
        client_order_id=raw.get("clientOrderId"),
        symbol=raw.get("symbol", symbol),
        side=raw.get("side", side),
        order_type=raw.get("type", order_type),
        orig_qty=raw.get("origQty", str(quantity)),
        executed_qty=raw.get("executedQty", "0"),
        avg_price=raw.get("avgPrice", "0"),
        status=raw.get("status", ""),
        raw=raw,
    )

    logger.info(
        "Order placed successfully | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result


def format_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
    stop_price: Decimal | None = None,
) -> str:
    """Return a human-readable order request summary for CLI display."""
    lines = [
        "─" * 46,
        "  ORDER REQUEST SUMMARY",
        "─" * 46,
        f"  Symbol     : {symbol}",
        f"  Side       : {side}",
        f"  Type       : {order_type}",
        f"  Quantity   : {quantity}",
    ]
    if price is not None:
        lines.append(f"  Price      : {price}")
    if stop_price is not None:
        lines.append(f"  Stop Price : {stop_price}")
    lines.append("─" * 46)
    return "\n".join(lines)


def format_order_result(result: OrderResult) -> str:
    """Return a human-readable order response for CLI display."""
    if not result.success:
        return (
            "\n  ✗ ORDER FAILED\n"
            f"  Error: {result.error}\n"
        )

    avg = result.avg_price if result.avg_price not in ("", "0", "0.00000000") else "N/A (pending fill)"
    lines = [
        "─" * 46,
        "  ORDER RESPONSE",
        "─" * 46,
        f"  Order ID    : {result.order_id}",
        f"  Cl. Order ID: {result.client_order_id}",
        f"  Symbol      : {result.symbol}",
        f"  Side        : {result.side}",
        f"  Type        : {result.order_type}",
        f"  Orig Qty    : {result.orig_qty}",
        f"  Executed Qty: {result.executed_qty}",
        f"  Avg Price   : {avg}",
        f"  Status      : {result.status}",
        "─" * 46,
        "  ✓ Order placed successfully!",
        "─" * 46,
    ]
    return "\n".join(lines)
