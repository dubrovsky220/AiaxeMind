"""
Central logging configuration for AiaxeMind.

Provides:
- JSON-formatted logs on stdout for easy ingestion/aggregation
- setup_logging() to initialize the logging system
- get_logger(name) to obtain module-specific loggers
- Support for structured logging with extra context fields

Usage:
    from src.core.logging_config import setup_logging, get_logger

    setup_logging(level="INFO")
    logger = get_logger(__name__)
    logger.info("Operation completed", extra={"document_id": doc_id})
"""

import logging
import sys

try:
    from pythonjsonlogger.json import jsonlogger  # type: ignore
except ImportError:
    jsonlogger = None  # Fallback if package isn't installed


def setup_logging(level: str = "INFO") -> None:
    """
    Initialize the logging system with JSON formatting.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Note:
        This function is idempotent - calling it multiple times won't
        duplicate handlers.
    """
    root_logger = logging.getLogger()

    # Don't duplicate handlers if setup is called again
    if root_logger.handlers:
        return

    root_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)

    if jsonlogger:
        # JSON format with common fields; add extra fields via logger calls
        formatter = jsonlogger.JsonFormatter(
            fmt=(
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "message": "%(message)s", '
                '"thread": "%(threadName)s", "file": "%(filename)s", '
                '"line": %(lineno)d}'
            )
        )
    else:
        # Lightweight fallback if python-json-logger isn't installed
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Logger instance configured with the global settings

    Example:
        logger = get_logger(__name__)
        logger.info("Processing started", extra={"doc_id": "123"})
    """
    return logging.getLogger(name)
