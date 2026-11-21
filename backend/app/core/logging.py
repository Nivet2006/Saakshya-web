"""Structured logging with default PHI/raw-speech redaction."""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any

from app.core.config import get_settings


def ensure_utf8_stdio() -> None:
    """Reconfigure stdout/stderr to UTF-8 on Windows to prevent cp1252 Indic crashes."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(Exception):
                reconfigure(encoding="utf-8", errors="replace")


def configure_logging(level: str | None = None) -> None:
    """Configure root Python logging with a clean structured format."""
    ensure_utf8_stdio()
    settings = get_settings()
    resolved_level = (level or settings.log_level or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, resolved_level, logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    # Keep noisy transport loggers quiet
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def safe_text_preview(text: str, *, redact: bool | None = None) -> str:
    """Redact raw speech text when LOG_REDACT_PHI is enabled."""
    if redact is None:
        redact = get_settings().log_redact_phi
    if redact:
        return f"<redacted len={len(text)}>"
    snippet = text.replace("\n", " ").strip()
    return snippet[:120] + ("..." if len(snippet) > 120 else "")


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Emit a key=value structured log line without leaking secrets."""
    pairs = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("event=%s %s", event, pairs)

