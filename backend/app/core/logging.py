# =============================================================================
# Logging Configuration - Loguru
# Structured logging with rotation and formatting
# =============================================================================

import sys
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    """Configure application-wide logging with loguru."""

    # Remove default handler
    logger.remove()

    # Console handler with colored output
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )

    # File handler with rotation
    logger.add(
        "logs/uniconnect_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG" if settings.DEBUG else "INFO",
        enqueue=True,  # Thread-safe
    )

    # Error-specific log file
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="60 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        enqueue=True,
    )

    logger.info(f"Logging initialized for {settings.APP_NAME} v{settings.APP_VERSION}")
