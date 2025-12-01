"""
데이터 저장/로드 헬퍼
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.file_manager import FileManager
from utils.logger import logger
from uuid import uuid4


@dataclass(frozen=True)
class StorageConfig:
    """
    데이터 저장 구조 정의
    """

    base_dir: str = "data"
    trends_dir: str = "trends"
    products_dir: str = "products"
    posts_dir: str = "posts"
    logs_dir: str = "logs"
    keyword_history_file: str = "keyword_history.json"
    keyword_history_limit: int = 50


class DataStorage:
    """
    트렌드/상품/포스트/로그 데이터를 파일로 저장/로드하는 헬퍼
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        self.file_manager = FileManager(base_dir=self.config.base_dir)
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """
        필요한 하위 디렉토리를 모두 생성합니다.
        """
        base_path = Path(self.file_manager.base_dir)
        for subdir in (
            self.config.trends_dir,
            self.config.products_dir,
            self.config.posts_dir,
            self.config.logs_dir,
        ):
            (base_path / subdir).mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()

    def generate_run_id(self) -> str:
        """
        파이프라인 실행 단위를 식별하기 위한 run_id를 생성합니다.
        """
        return datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]

    def _subdir_path(self, subdir: str) -> Path:
        return Path(self.file_manager.base_dir) / subdir

    def _list_json_files(self, subdir: str, pattern: str = "*.json") -> List[Path]:
        directory = self._subdir_path(subdir)
        if not directory.exists():
            return []
        return sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    def _read_json_file(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with path.open("r", encoding="utf-8") as fp:
                return json.load(fp)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"JSON 파일을 읽지 못했습니다 ({path}): {exc}")
            return None

    def _build_payload(self, items: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = metadata.copy() if metadata else {}
        meta.setdefault("count", len(items))
        meta.setdefault("saved_at", self._timestamp())
        return {"metadata": meta, "items": items}

    # Trends -----------------------------------------------------------------
    def save_trends(self, keywords: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None, filename: Optional[str] = None) -> Path:
        """
        트렌드 키워드 배치를 저장합니다.
        """
        payload = self._build_payload(keywords, metadata)
        filename = filename or self.file_manager.generate_filename("trends", "json")
        return self.file_manager.save_json(payload, filename, subdir=self.config.trends_dir)

    # Products ---------------------------------------------------------------
    def save_products(self, products: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None, filename: Optional[str] = None) -> Path:
        payload = self._build_payload(products, metadata)
        filename = filename or self.file_manager.generate_filename("products", "json")
        return self.file_manager.save_json(payload, filename, subdir=self.config.products_dir)

    # Posts ------------------------------------------------------------------
    def save_post(self, post: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None, filename: Optional[str] = None) -> Path:
        payload = {
            "metadata": metadata or {"saved_at": self._timestamp()},
            "post": post,
        }
        filename = filename or self.file_manager.generate_filename("post", "json")
        return self.file_manager.save_json(payload, filename, subdir=self.config.posts_dir)

    # Logs -------------------------------------------------------------------
    def save_run_log(self, log_item: Dict[str, Any], filename: Optional[str] = None) -> Path:
        enriched = log_item.copy()
        enriched.setdefault("timestamp", self._timestamp())
        filename = filename or self.file_manager.generate_filename("run", "json")
        return self.file_manager.save_json(enriched, filename, subdir=self.config.logs_dir)

    # Keyword history --------------------------------------------------------
    def save_keyword_history(self, history: List[Dict[str, Any]]) -> Path:
        """
        최근 키워드 선택 히스토리를 저장합니다.
        """
        trimmed_history = history[-self.config.keyword_history_limit :]
        path = Path(self.file_manager.base_dir) / self.config.logs_dir / self.config.keyword_history_file
        payload = {
            "metadata": {
                "saved_at": self._timestamp(),
                "count": len(trimmed_history),
            },
            "history": trimmed_history,
        }
        with path.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
        return path

    def load_keyword_history(self) -> List[Dict[str, Any]]:
        """
        키워드 히스토리를 로드합니다.
        """
        path = self._subdir_path(self.config.logs_dir) / self.config.keyword_history_file
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except (json.JSONDecodeError, OSError):
            logger.warning("키워드 히스토리 파일을 읽을 수 없습니다. 새로 생성합니다.")
            return []

        history = payload.get("history")
        if not isinstance(history, list):
            return []

        sanitized: List[Dict[str, Any]] = []
        for item in history[-self.config.keyword_history_limit :]:
            if isinstance(item, dict) and isinstance(item.get("keyword"), str):
                sanitized.append(item)
        return sanitized

    # Retrieval helpers ------------------------------------------------------
    def load_latest_trends(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        가장 최근에 저장된 트렌드 파일에서 데이터를 로드합니다.
        """
        files = self._list_json_files(self.config.trends_dir)
        if not files:
            return []
        payload = self._read_json_file(files[0])
        if not payload:
            return []
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return items[:limit] if isinstance(limit, int) and limit > 0 else items

    def load_latest_products(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        files = self._list_json_files(self.config.products_dir)
        if not files:
            return []
        payload = self._read_json_file(files[0])
        if not payload:
            return []
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return items[:limit] if isinstance(limit, int) and limit > 0 else items

    def load_latest_post(self) -> Optional[Dict[str, Any]]:
        files = self._list_json_files(self.config.posts_dir)
        if not files:
            return None
        payload = self._read_json_file(files[0])
        if not payload:
            return None
        return payload.get("post")

    def load_recent_run_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        files = self._list_json_files(self.config.logs_dir, pattern="run_*.json")
        logs: List[Dict[str, Any]] = []
        for path in files[:limit]:
            payload = self._read_json_file(path)
            if isinstance(payload, dict):
                logs.append(payload)
        return logs
