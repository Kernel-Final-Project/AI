from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv as _load_dotenv
except ImportError:  # pragma: no cover
    _load_dotenv = None  # type: ignore


def load_env_from_default_locations(anchor: Path | None = None) -> bool:
    """루트/`remAI` 디렉터리를 거슬러 올라가며 .env를 로드한다."""
    if _load_dotenv is None:
        return False

    base = anchor or Path(__file__).resolve()
    candidates: list[Path] = []
    for parent in base.parents:
        candidates.append(parent / ".env")
        candidates.append(parent / "ai_integration" / ".env")

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            _load_dotenv(candidate)  # type: ignore[operator]
            return True
    return False


def configure_logging(logs_dir: Path, level: str = "INFO") -> Path:
    """콘솔+파일 핸들러를 구성하고 생성된 로그 파일 경로를 돌려준다."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"pipeline-{timestamp}.log"

    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # 기존 핸들러 제거 후 새 콘솔/파일 핸들러 등록
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.debug("로그 파일 초기화: %s", log_file)
    return log_file


def write_json(path: Path, data: Any) -> None:
    """ensure_ascii False 옵션으로 JSON 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    """UTF-8 JSON을 읽어 dict로 돌려준다."""
    return json.loads(path.read_text(encoding="utf-8"))
