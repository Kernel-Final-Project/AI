"""
트렌드 상품 1개 랜덤 선택 모듈
AI1 담당
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Set

from utils.logger import logger

DEFAULT_HISTORY_LIMIT = 50


def _normalize_keyword(keyword: str) -> str:
    return " ".join(keyword.strip().lower().split())


def _filter_used_keywords(keywords: List[Dict], history: Sequence[Dict], history_limit: int) -> List[Dict]:
    if not history:
        return keywords

    normalized_used: Set[str] = set()
    for item in history[-history_limit:]:
        value = item.get("keyword")
        if not isinstance(value, str):
            continue
        normalized_used.add(_normalize_keyword(value))

    fresh_keywords: List[Dict] = []
    for item in keywords:
        keyword = str(item.get("keyword", "")).strip()
        if not keyword:
            continue
        normalized = _normalize_keyword(keyword)
        if normalized in normalized_used:
            continue
        fresh_keywords.append(item)

    if not fresh_keywords:
        logger.info("사용하지 않은 키워드가 없어 히스토리를 초기화합니다.")
        return keywords
    return fresh_keywords


def select_random_keyword(
    keywords: List[Dict],
    history: Optional[Sequence[Dict]] = None,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    weighted: bool = False,
) -> Optional[Dict]:
    """
    수집된 키워드 중 1개를 랜덤으로 선택합니다.
    최근 히스토리에 포함된 키워드는 피합니다.
    weighted=True인 경우 score 기반 가중치 랜덤을 사용합니다.
    """
    if not keywords:
        logger.warning("선택할 키워드가 없습니다.")
        return None

    candidates = _filter_used_keywords(keywords, history or [], history_limit)

    if weighted:
        weights = []
        for item in candidates:
            raw_score = item.get("score", 0)
            try:
                weight = max(float(raw_score), 1.0)
            except (TypeError, ValueError):
                weight = 1.0
            weights.append(weight)
        selected = random.choices(candidates, weights=weights, k=1)[0]
    else:
        selected = random.choice(candidates)

    logger.info(f"선택된 키워드: {selected.get('keyword', 'Unknown')}")
    return selected


def rank_keywords_by_score(keywords: List[Dict]) -> List[Dict]:
    """
    키워드를 점수 기반으로 정렬합니다.
    """
    logger.info(f"{len(keywords)}개 키워드 점수 기반 정렬")
    sorted_keywords = sorted(keywords, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_keywords
