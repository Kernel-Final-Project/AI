"""
웹훅으로 업로드 결과를 통지하기 위한 간단한 헬퍼.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .logger import logger
from .results import UploadResult


def send_webhook(
    url: str,
    payload: Dict[str, Any],
    *,
    token: Optional[str] = None,
    timeout: int = 5,
) -> bool:
    """
    POST JSON webhook.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json; charset=utf-8")
    request.add_header("Content-Length", str(len(data)))
    if token:
        request.add_header("X-WEBHOOK-SECRET", token)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            logger.info("웹훅 전송 성공 (status=%s)", status)
            return 200 <= status < 300
    except urllib.error.HTTPError as exc:
        logger.error(
            "웹훅 전송 실패(HTTP %s): %s",
            exc.code,
            exc.read().decode("utf-8", errors="ignore"),
        )
    except urllib.error.URLError as exc:
        logger.error("웹훅 전송 실패(URL Error): %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("웹훅 전송 중 알 수 없는 오류: %s", exc)
    return False


def notify_upload_result(
    result: UploadResult,
    *,
    webhook_url: Optional[str],
    token: Optional[str] = None,
    timeout: int = 5,
    work_id: Optional[str] = None,
    completed_at: Optional[str] = None,
    is_test: bool = False,
    log: Optional[logging.Logger] = None,
) -> None:
    """
    업로드 결과를 로그로 남기고 필요 시 웹훅으로 전송한다.
    """
    if not webhook_url:
        return

    logger_to_use = log or logger
    payload = result.to_payload(work_id=work_id)
    payload["isTest"] = bool(is_test)
    if completed_at:
        payload["completedAt"] = completed_at
    logger_to_use.info(
        "웹훅 전송: url=%s timeout=%s status=%s",
        webhook_url,
        timeout,
        payload.get("status"),
    )
    success = send_webhook(webhook_url, payload, token=token, timeout=timeout)
    if not success:
        logger_to_use.warning("웹훅 전송 실패(work_id=%s)", work_id)
