"""
Binance Futures Testnet REST client.

Handles:
- HMAC-SHA256 request signing
- Timestamping
- HTTP error surfacing
- Structured request/response logging
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from decimal import Decimal
from typing import Any

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # milliseconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error payload."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message} (HTTP {status_code})")


class BinanceFuturesClient:
    """
    Lightweight wrapper around the Binance USDT-M Futures Testnet REST API.

    Usage
    -----
    client = BinanceFuturesClient(api_key="...", api_secret="...")
    response = client.new_order(symbol="BTCUSDT", side="BUY",
                                order_type="MARKET", quantity=Decimal("0.001"))
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceFuturesClient initialised — base_url=%s", self._base_url)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict[str, Any]:
        """
        Place a new futures order.

        Parameters
        ----------
        symbol      : Trading pair, e.g. "BTCUSDT"
        side        : "BUY" or "SELL"
        order_type  : "MARKET", "LIMIT", or "STOP_MARKET"
        quantity    : Order quantity in base asset
        price       : Required for LIMIT orders
        stop_price  : Required for STOP_MARKET orders
        time_in_force: GTC / IOC / FOK (LIMIT only)
        reduce_only : If True, the order can only reduce an existing position
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
            "reduceOnly": str(reduce_only).upper(),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("stop_price is required for STOP_MARKET orders.")
            params["stopPrice"] = str(stop_price)

        return self._signed_post("/fapi/v1/order", params)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Query an existing order by orderId."""
        return self._signed_get(
            "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}
        )

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel an open order."""
        return self._signed_delete(
            "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}
        )

    def get_account(self) -> dict[str, Any]:
        """Return account information including balances."""
        return self._signed_get("/fapi/v2/account", {})

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            resp = self._session.get(
                f"{self._base_url}/fapi/v1/ping", timeout=self._timeout
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_get(self, path: str, params: dict) -> dict[str, Any]:
        params = {**params, "timestamp": self._timestamp(), "recvWindow": RECV_WINDOW}
        qs = urllib.parse.urlencode(params)
        qs += f"&signature={self._sign(qs)}"
        url = f"{self._base_url}{path}?{qs}"
        logger.debug("GET %s", url)
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.error("Network error on GET %s: %s", path, exc)
            raise
        return self._handle_response(resp)

    def _signed_post(self, path: str, params: dict) -> dict[str, Any]:
        params = {**params, "timestamp": self._timestamp(), "recvWindow": RECV_WINDOW}
        qs = urllib.parse.urlencode(params)
        signature = self._sign(qs)
        body = f"{qs}&signature={signature}"
        url = f"{self._base_url}{path}"
        logger.debug("POST %s  body=%s", url, body)
        try:
            resp = self._session.post(url, data=body, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.error("Network error on POST %s: %s", path, exc)
            raise
        return self._handle_response(resp)

    def _signed_delete(self, path: str, params: dict) -> dict[str, Any]:
        params = {**params, "timestamp": self._timestamp(), "recvWindow": RECV_WINDOW}
        qs = urllib.parse.urlencode(params)
        qs += f"&signature={self._sign(qs)}"
        url = f"{self._base_url}{path}?{qs}"
        logger.debug("DELETE %s", url)
        try:
            resp = self._session.delete(url, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.error("Network error on DELETE %s: %s", path, exc)
            raise
        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> dict[str, Any]:
        logger.debug("Response HTTP %s: %s", resp.status_code, resp.text[:500])
        try:
            data = resp.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %s): %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return {}

        if not resp.ok:
            code = data.get("code", resp.status_code)
            message = data.get("msg", resp.text)
            logger.error("API error code=%s message=%s", code, message)
            raise BinanceAPIError(resp.status_code, code, message)

        logger.debug("API response: %s", data)
        return data
