"""
Input validation for trading bot CLI parameters.
All validation raises ValueError with a human-readable message on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol or raise ValueError."""
    symbol = symbol.strip().upper()
    if not symbol or not symbol.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphanumeric, e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return normalised side (BUY/SELL) or raise ValueError."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return normalised order type or raise ValueError."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Return quantity as Decimal or raise ValueError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: str | float | None, order_type: str) -> Decimal | None:
    """
    Validate price field.

    - MARKET / STOP_MARKET orders: price must be None / omitted.
    - LIMIT orders: price is required and must be positive.
    """
    order_type = order_type.strip().upper()

    if order_type in ("MARKET", "STOP_MARKET"):
        if price is not None:
            raise ValueError(f"Price must not be provided for {order_type} orders.")
        return None

    # LIMIT — price required
    if price is None:
        raise ValueError(f"Price is required for {order_type} orders.")
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
) -> dict:
    """
    Run all validators and return a clean params dict.
    Raises ValueError on the first failure encountered.
    """
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
    }
