"""
Structured JSON Logger with Automated PII Redaction.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from backend.app.api.logging.pii_masker import mask_dict


class JsonPiiRedactingFormatter(logging.Formatter):
    """Custom formatter rendering structured JSON logs with PII suppression."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields if present
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry["data"] = mask_dict(record.extra_fields)

        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Configures and returns a PII-safe institutional logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonPiiRedactingFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
