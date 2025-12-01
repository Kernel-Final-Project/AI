"""
Simple logger configuration for the worker.
"""
from __future__ import annotations

import os
from pathlib import Path

from blog_upload_module.logger import setup_logger as base_setup_logger


def _resolve_log_dir() -> Path:
    custom_dir = os.getenv("WORKER_LOG_DIR")
    if custom_dir:
        return Path(custom_dir).expanduser().resolve()
    return Path.cwd() / "logs"


logger = base_setup_logger(
    name="blog_worker",
    level=os.getenv("WORKER_LOG_LEVEL", "INFO"),
    log_dir=_resolve_log_dir(),
    file_name=os.getenv("WORKER_LOG_FILE", "blog_worker.log"),
)
