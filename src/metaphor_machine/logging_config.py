"""Centralised logging — writes to data/logs/metaphor-machine.log + stderr.

Use this from agents and pipeline by calling `get_logger(__name__)`. Set up
once at import time (idempotent via the `_configured` sentinel).

Why a file: Streamlit's stdout/stderr only shows you the current process —
once you Ctrl+C, history is gone. The log file persists across runs so you
can diagnose what happened in yesterday's pipeline call, including silent
Transformer parallel failures that the UI only summarized.

Rotation: 2 MB per file, keep 5 backups → ~10 MB worst case on disk.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(os.getenv("METAPHOR_LOG_DIR", "./data/logs"))
_LOG_FILE = _LOG_DIR / "metaphor-machine.log"
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_BACKUP_COUNT = 5

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger. Safe to call multiple times."""
    global _configured
    if _configured:
        return

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only filesystem or permission issue — fall back to stderr-only.
        # Don't crash the app over a logging concern.
        pass

    root = logging.getLogger("metaphor_machine")
    root.setLevel(level)
    # Don't duplicate when Streamlit re-imports modules.
    root.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — best effort
    if _LOG_DIR.exists():
        try:
            fh = RotatingFileHandler(
                _LOG_FILE,
                maxBytes=_MAX_BYTES,
                backupCount=_BACKUP_COUNT,
                encoding="utf-8",
            )
            fh.setFormatter(fmt)
            fh.setLevel(level)
            root.addHandler(fh)
        except OSError:
            pass

    # Stderr handler so devs see things in the terminal too
    sh = logging.StreamHandler(stream=sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(level)
    root.addHandler(sh)

    root.propagate = False  # don't double-log via Python's root logger
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger. Auto-configures on first call."""
    if not _configured:
        setup_logging()
    # Always namespace under metaphor_machine so we can filter cleanly.
    if not name.startswith("metaphor_machine"):
        name = f"metaphor_machine.{name}"
    return logging.getLogger(name)


def log_file_path() -> Path:
    """Where the log file lives — for the UI to tail."""
    return _LOG_FILE


def tail_log(n_lines: int = 80) -> str:
    """Return the last n lines of the log file, or empty string if missing."""
    if not _LOG_FILE.exists():
        return ""
    try:
        # Read whole file then tail — files are small (2 MB cap)
        text = _LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[-n_lines:])
