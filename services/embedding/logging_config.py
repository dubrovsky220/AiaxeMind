"""
Logging configuration for Embedding Service.

Provides JSON-formatted logs for easy integration with log aggregation systems.
"""

import logging
import sys

try:
    from pythonjsonlogger.json import jsonlogger  # type: ignore
except ImportError:
    jsonlogger = None


def setup_logging(level: str = "INFO") -> None:
    """
    Initialize logging for the embedding service.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    root_logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)

    if jsonlogger:
        formatter = jsonlogger.JsonFormatter(
            fmt=(
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"service": "embedding", "logger": "%(name)s", '
                '"message": "%(message)s", "file": "%(filename)s", '
                '"line": %(lineno)d}'
            )
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - [embedding] %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the embedding service.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
