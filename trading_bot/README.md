# Binance Futures Testnet Trading Bot

A clean, structured Python CLI application to place orders on the **Binance USDT-M Futures Testnet**.

Supports MARKET, LIMIT, and STOP_MARKET orders with full input validation, structured logging, and clear CLI output.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py            # Order placement logic + result formatting
│   ├── validators.py        # Input validation (raises ValueError on bad input)
│   └── logging_config.py   # Logging setup (file + console handlers)
├── cli.py                   # CLI entry point (argparse)
├── logs/
│   └── trading_bot_YYYYMMDD.log   # Auto-created on first run
├── README.md
└── requirements.txt
```

### Layer separation

| Layer | File | Responsibility |
|---|---|---|
| CLI | `cli.py` | Parse args, validate, print output, handle exit codes |
| Orders | `bot/orders.py` | Orchestrate order flow, return `OrderResult` |
| Client | `bot/client.py` | Sign requests, call REST API, raise `BinanceAPIError` |
| Validators | `bot/validators.py` | Pure functions — validate and normalise inputs |
| Logging | `bot/logging_config.py` | Configure file + console handlers |

---

## Setup

### 1. Binance Futures Testnet credentials

1. Register at [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in and navigate to **API Management** → Generate a key pair
3. Copy your **API Key** and **Secret Key**

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set credentials

**Option A — environment variables (recommended)**
```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B — CLI flags (not recommended for production)**
```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET ...
```

---

## Usage

```
python cli.py [--api-key KEY] [--api-secret SECRET]
              --symbol SYMBOL --side {BUY,SELL}
              --type {MARKET,LIMIT,STOP_MARKET}
              --quantity QTY
              [--price PRICE]
              [--stop-price STOP_PRICE]
              [--time-in-force {GTC,IOC,FOK}]
              [--reduce-only]
              [--dry-run]
              [--log-level {DEBUG,INFO,WARNING,ERROR}]
```

### Examples

**Market BUY**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

**Limit SELL**
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 71000
```

**Stop-Market BUY (bonus order type)**
```bash
python cli.py --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.01 --stop-price 3800
```

**Dry-run (validate without sending)**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run
```

**Verbose console output**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --log-level INFO
```

---

## Sample Output

### Market BUY
```
──────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
──────────────────────────────────────────────
  Sending order to Binance Futures Testnet …

──────────────────────────────────────────────
  ORDER RESPONSE
──────────────────────────────────────────────
  Order ID    : 4073834274
  Cl. Order ID: x-Cb7ytekJca3e5b2f789a
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Orig Qty    : 0.001
  Executed Qty: 0.001
  Avg Price   : 69412.30000
  Status      : FILLED
──────────────────────────────────────────────
  ✓ Order placed successfully!
──────────────────────────────────────────────
```

### Validation error
```
  ✗ Validation error: Quantity must be greater than zero, got -5.
```

---

## Logging

All runs append to `logs/trading_bot_YYYYMMDD.log`:

- **File**: DEBUG level — full request body, raw API response, all info/error events
- **Console**: WARNING and above by default (use `--log-level INFO` or `DEBUG` for more)

Log format:
```
2025-06-07T09:12:03 | INFO     | trading_bot.orders | Order placed successfully | orderId=4073834274 status=FILLED executedQty=0.001 avgPrice=69412.30000
```

Sample log files covering a market order, limit order, stop-market order, and error cases are in `logs/trading_bot_20250607.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Invalid symbol / side / type | Validation error printed; exit code 1 |
| Negative or zero quantity | Validation error printed; exit code 1 |
| Missing price for LIMIT order | Validation error printed; exit code 1 |
| Missing stop-price for STOP_MARKET | Validation error printed; exit code 1 |
| API error (e.g. insufficient margin) | `BinanceAPIError` caught; error message printed; exit code 1 |
| Network failure / timeout | `requests.RequestException` caught; error message printed; exit code 1 |
| Missing API credentials | Clear message printed before any network call; exit code 1 |

---

## Bonus Feature

**Stop-Market orders** are supported as a third order type (`--type STOP_MARKET`). Pass the trigger price via `--stop-price`. When the market price reaches that level, the order becomes a market order and fills immediately.

---

## Assumptions

- Testnet base URL: `https://testnet.binancefuture.com` (USDT-M Futures)
- Default position mode: **One-way** (BOTH side). Hedge mode is not handled.
- `timeInForce` defaults to `GTC` for LIMIT orders.
- Quantity precision is passed as entered; Binance will reject values that don't match the symbol's `stepSize`. Check symbol info on the testnet dashboard.
- No retry logic — API or network errors are surfaced immediately.

---

## Requirements

- Python 3.8+
- `requests>=2.31.0`
