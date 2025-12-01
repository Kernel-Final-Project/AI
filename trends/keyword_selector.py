"""
키워드 선택/히스토리 관리 모듈
"""
from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from storage import DataStorage
from utils.logger import logger

DEFAULT_HISTORY_LIMIT = 50
DEFAULT_MAX_HISTORY_SIZE = 200
DEFAULT_WEIGHTED = True


def _normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.strip().lower().split())


def _extract_keyword(item: Union[str, Dict[str, Any]]) -> Optional[str]:
    if isinstance(item, str):
        value = item
    elif isinstance(item, dict):
        value = item.get("keyword") or item.get("name") or item.get("text")
    else:
        value = None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return None


def _filter_used_keywords(candidates: List[str], history: Sequence[str], history_limit: int) -> List[str]:
    if not history:
        return candidates

    normalized_used: Set[str] = set()
    for kw in history[-history_limit:]:
        normalized_used.add(_normalize_keyword(kw))

    fresh: List[str] = []
    for kw in candidates:
        norm = _normalize_keyword(kw)
        if norm in normalized_used:
            continue
        fresh.append(kw)

    if not fresh:
        logger.info("히스토리에 없는 후보가 없어 전체 후보를 사용합니다.")
        return candidates
    return fresh


def _prepare_candidates(raw_candidates: Iterable[Union[str, Dict[str, Any]]]) -> List[str]:
    prepared: List[str] = []
    seen: Set[str] = set()
    for item in raw_candidates:
        kw = _extract_keyword(item)
        if not kw:
            continue
        norm = _normalize_keyword(kw)
        if norm in seen:
            continue
        seen.add(norm)
        prepared.append(kw)
    return prepared


def _choose(candidates: List[str], weighted: bool = DEFAULT_WEIGHTED) -> Optional[str]:
    if not candidates:
        return None
    if not weighted:
        return random.choice(candidates)
    # 현재는 점수 정보가 없으므로 균등 가중치. 구조만 남겨둠.
    weights = [1.0 for _ in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def select_keyword(
    candidates: Iterable[Union[str, Dict[str, Any]]],
    *,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    weighted: bool = DEFAULT_WEIGHTED,
    max_history_size: int = DEFAULT_MAX_HISTORY_SIZE,
    storage: Optional[DataStorage] = None,
) -> Optional[str]:
    """
    히스토리를 참고하여 키워드 1개를 선택하고 히스토리에 기록합니다.
    """
    try:
        prepared_candidates = _prepare_candidates(candidates)
        if not prepared_candidates:
            logger.warning("선택할 후보 키워드가 없습니다.")
            return None

        store = storage or DataStorage()
        history = store.load_keyword_history(limit=history_limit)

        filtered = _filter_used_keywords(prepared_candidates, history, history_limit)
        selected = _choose(filtered, weighted=weighted)
        if not selected:
            selected = _choose(prepared_candidates, weighted=weighted)

        if not selected:
            logger.warning("키워드 선택에 실패했습니다.")
            return None

        store.append_keyword_history(selected, max_size=max_history_size)
        logger.info("선택된 키워드: %s", selected)
        return selected
    except Exception as exc:  # pragma: no cover - 안전장치
        logger.warning("키워드 선택 중 예외 발생: %s", exc)
        return None


def rank_keywords_by_score(keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    logger.info("%s개 키워드 점수 기반 정렬", len(keywords))
    return sorted(keywords, key=lambda x: x.get("score", 0), reverse=True)
