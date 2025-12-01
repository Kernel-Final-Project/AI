"""
blog_upload_module 전용 로거
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import IO, Optional

DEFAULT_LOG_DIR = Path(
    os.getenv("BLOG_UPLOAD_MODULE_LOG_DIR", Path.cwd() / "logs")
).resolve()


def _resolve_numeric_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)


def setup_logger(
    name: str = "blog_upload_module",
    level: str = "INFO",
    *,
    log_dir: Path | str | None = None,
    stream: IO[str] | None = None,
    file_name: Optional[str] = None,
) -> logging.Logger:
    """
    구성 가능한 로거 생성 헬퍼.
    `log_dir` 가 지정되지 않으면 현재 작업 디렉터리 기준 logs/ 를 사용한다.
    """
    logger = logging.getLogger(name)
    numeric_level = _resolve_numeric_level(level)
    logger.setLevel(numeric_level)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(stream or sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)
    logger.addHandler(console_handler)

    log_dir_path = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir_path / (file_name or f"{datetime.now():%Y%m%d}.log")

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def set_log_level(level: str, *, target: Optional[logging.Logger] = None) -> None:
    """
    런타임에 로깅 레벨을 조정한다.
    """
    numeric = _resolve_numeric_level(level)
    target_logger = target or logger
    target_logger.setLevel(numeric)
    for handler in target_logger.handlers:
        handler.setLevel(numeric)
