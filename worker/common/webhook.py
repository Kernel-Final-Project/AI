from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def post_webhook(url: str, secret: Optional[str], payload: Dict[str, Any], timeout: float = 10.0) -> Any:
    """공통 웹훅 호출: Authorization 헤더 적용, 2xx가 아니면 예외."""
    if not url:
        raise ValueError("웹훅 URL이 비어 있습니다.")
    if not secret:
        raise ValueError("웹훅 secret이 설정되지 않았습니다.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": secret,
    }

    logger.info("Calling webhook: %s", url)
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Webhook 호출 실패({resp.status_code}): {resp.text}")

    if not resp.content:
        return None

    try:
        return resp.json()
    except ValueError:
        return resp.text
