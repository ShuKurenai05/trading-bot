"""
Logging configuration for the trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    - File handler: logs/trading_bot_YYYYMMDD.log  (DEBUG and above)
    - Console handler: WARNING and above (keeps CLI output clean)
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_filename = os.path.join(
        LOG_DIR, f"trading_bot_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    console_fmt = logging.Formatter(fmt="%(levelname)-8s | %(message)s")

    # File handler — full DEBUG detail
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_fmt)

    # Console handler — WARNING+ only so CLI stays readable
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, log_level.upper(), logging.WARNING))
    ch.setFormatter(console_fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Logging initialised — file: %s", log_filename)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger scoped to *name* under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
