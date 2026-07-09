"""Centralized logging configuration."""

import logging

from app.core.config import settings


def configure_logging() -> None:
    """Configure the root logger with a consistent format and level.

    The log level is driven by the ``LOG_LEVEL`` environment variable.
    """

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
