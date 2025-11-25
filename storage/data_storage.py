"""
데이터 저장/로드 헬퍼
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from utils.file_manager import FileManager
from utils.logger import logger


@dataclass(frozen=True)
class StorageConfig:
    """
    데이터 저장 구조 정의
    """

    base_dir: str = "data"
    trends_dir: str = "trends"
    keywords_dir: str = "keywords"
    products_dir: str = "products"
    posts_dir: str = "posts"
    logs_dir: str = "logs"
    keyword_history_file: str = "keyword_history.json"


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
            self.config.keywords_dir,
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
        포맷: YYYYMMDD_HHMMSS
        """
        return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

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

    def _save_run_payload(self, subdir: str, run_id: str, payload: Dict[str, Any]) -> Path:
        """
        run_id를 파일명으로 하여 지정 디렉토리에 저장
        """
        filename = f"{run_id}.json"
        return self.file_manager.save_json(payload, filename, subdir=subdir)

    # Trends -----------------------------------------------------------------
    def save_trends(self, run_id: str, payload: Dict[str, Any]) -> Path:
        """
        트렌드 키워드 배치를 저장합니다.
        """
        payload.setdefault("run_id", run_id)
        payload.setdefault("saved_at", self._timestamp())
        return self._save_run_payload(self.config.trends_dir, run_id, payload)

    # Keywords ---------------------------------------------------------------
    def save_keywords(self, run_id: str, keywords: Union[List[Any], Dict[str, Any]], meta: Optional[Dict[str, Any]] = None) -> Path:
        """
        키워드 선택/후보 결과를 저장합니다.
        """
        payload: Dict[str, Any]
        if isinstance(keywords, dict):
            payload = keywords.copy()
        else:
            payload = {"keywords": keywords}
        payload.setdefault("run_id", run_id)
        payload.setdefault("meta", meta or {})
        payload.setdefault("saved_at", self._timestamp())
        return self._save_run_payload(self.config.keywords_dir, run_id, payload)

    # Products ---------------------------------------------------------------
    def save_products(self, run_id: str, products: List[Dict[str, Any]], meta: Optional[Dict[str, Any]] = None) -> Path:
        payload = self._build_payload(products, meta)
        payload.setdefault("run_id", run_id)
        return self._save_run_payload(self.config.products_dir, run_id, payload)

    # Posts ------------------------------------------------------------------
    def save_post(self, run_id: str, post: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> Path:
        payload = {"metadata": meta or {"saved_at": self._timestamp()}, "post": post, "run_id": run_id}
        return self._save_run_payload(self.config.posts_dir, run_id, payload)

    # Logs -------------------------------------------------------------------
    def save_run_log(self, run_id: str, log_item: Dict[str, Any]) -> Path:
        enriched = log_item.copy()
        enriched.setdefault("timestamp", self._timestamp())
        enriched.setdefault("run_id", run_id)
        return self._save_run_payload(self.config.logs_dir, run_id, enriched)

    # Keyword history --------------------------------------------------------
    def load_keyword_history(self, limit: Optional[int] = None) -> List[str]:
        """
        키워드 히스토리를 로드합니다.
        """
        path = self._subdir_path(self.config.logs_dir) / self.config.keyword_history_file
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8") as fp:
                payload = json.load(fp)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("키워드 히스토리를 읽을 수 없습니다: %s", exc)
            return []

        history = payload.get("history")
        if not isinstance(history, list):
            return []

        keywords: List[str] = []
        for item in history:
            if isinstance(item, dict):
                value = item.get("keyword")
            else:
                value = item
            if isinstance(value, str) and value.strip():
                keywords.append(value.strip())
        if limit and limit > 0:
            return keywords[-limit:]
        return keywords

    def append_keyword_history(self, keyword: str, max_size: int = 200) -> None:
        """
        새 키워드를 히스토리에 추가하고 max_size를 넘으면 오래된 항목을 제거합니다.
        """
        if not keyword:
            return
        path = self._subdir_path(self.config.logs_dir) / self.config.keyword_history_file
        existing = self.load_keyword_history()  # already handles missing
        existing.append(keyword)
        trimmed = existing[-max_size:]
        payload = {
            "metadata": {"saved_at": self._timestamp(), "count": len(trimmed)},
            "history": [{"keyword": k} for k in trimmed],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning("키워드 히스토리 저장 실패: %s", exc)

    # Retrieval helpers ------------------------------------------------------
    def _load_latest_from(self, subdir: str) -> Optional[Dict[str, Any]]:
        files = self._list_json_files(subdir)
        if not files:
            return None
        return self._read_json_file(files[0])

    def load_latest_trends(self) -> Optional[Dict[str, Any]]:
        return self._load_latest_from(self.config.trends_dir)

    def load_latest_keywords(self) -> Optional[Dict[str, Any]]:
        return self._load_latest_from(self.config.keywords_dir)

    def load_latest_products(self) -> Optional[Dict[str, Any]]:
        return self._load_latest_from(self.config.products_dir)

    def load_latest_posts(self) -> Optional[Dict[str, Any]]:
        return self._load_latest_from(self.config.posts_dir)

    def load_recent_run_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        files = self._list_json_files(self.config.logs_dir, pattern="*.json")
        logs: List[Dict[str, Any]] = []
        for path in files[:limit]:
            payload = self._read_json_file(path)
            if isinstance(payload, dict):
                logs.append(payload)
        return logs
