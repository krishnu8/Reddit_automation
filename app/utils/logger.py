"""
Application-wide logging configuration using Loguru.

Provides a pre-configured logger instance that writes to both
the console and a rotating log file.
"""

import sys
from loguru import logger

from app.config import log_cfg


def setup_logger() -> None:
    """
    Configure loguru with console + file sinks.

    Call once at application startup (main.py).
    """
    # Remove the default stderr handler so we can customise it
    logger.remove()

    # ── Console sink ────────────────────────────────────────────
    logger.add(
        sys.stderr,
        level=log_cfg.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # ── File sink (rotating, 50 MB max, keep 7 days) ───────────
    log_path = log_cfg.absolute_log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        level=log_cfg.log_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        rotation="50 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,  # thread-safe
    )

    logger.info("Logger initialised — level={}, file={}", log_cfg.log_level, log_path)
