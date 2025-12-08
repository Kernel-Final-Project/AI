from __future__ import annotations

import json
import logging
import os
import signal
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pika
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from keywordCrawler.services import crawl_keywords_to_list
from select_keyword.selector import SelectionResult, select_from_lists

logger = logging.getLogger(__name__)


class TrendCategory(BaseModel):
    category1: str
    category2: Optional[str] = None
    category3: Optional[str] = None


class ProductInfo(BaseModel):
    productId: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    productUrl: Optional[str] = None


class WebhookUrls(BaseModel):
    keywordSelect: str
    productSelect: Optional[str] = None
    contentGenerate: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    workId: int
    hasCrawledItems: Optional[bool] = None
    recentTrendKeywords: List[str] = Field(default_factory=list)
    crawledProducts: Optional[List[ProductInfo]] = None
    recentlyUsedProducts: Optional[List[str]] = None  # URL 문자열 리스트
    trendCategory: TrendCategory
    siteUrl: Optional[str] = None
    webhookSecret: Optional[str] = None  # 키워드 선택용 헤더는 별도 env 사용
    webhookUrls: WebhookUrls


def _load_env() -> None:
    load_dotenv()


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value is not None else default


def select_keywords_for_request(req: ContentGenerateRequest) -> SelectionResult:
    candidates = crawl_keywords_to_list(
        req.trendCategory.category1,
        req.trendCategory.category2,
        req.trendCategory.category3,
        headless=True,
    )
    recent_keywords = req.recentTrendKeywords or []
    used_urls = [url.strip() for url in (req.recentlyUsedProducts or []) if url and url.strip()]
    exclude_list = [kw for kw in recent_keywords if kw] + used_urls

    selections = select_from_lists(
        candidates,
        exclude=exclude_list,
        top_n=1,
    )
    return selections[0]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def post_keyword_webhook(
    req: ContentGenerateRequest,
    selection: SelectionResult,
    timeout: float = 10.0,
    auth_secret: str | None = None,
) -> None:
    # 키워드 웹훅은 Authorization 헤더 + KEYWORD_SELECT_WEBHOOK_SECRET 기반으로 동작
    if not auth_secret:
        raise RuntimeError("KEYWORD_SELECT_WEBHOOK_SECRET가 설정되지 않았습니다.")

    url = req.webhookUrls.keywordSelect
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_secret,
    }

    payload: Dict[str, Any] = {
        "workId": req.workId,
        "keyword": selection.keyword,
        "success": True,
        "message": selection.reason,
        "startedAt": _now_iso(),
        "completedAt": _now_iso(),
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Webhook 호출 실패({resp.status_code}): {resp.text}")


def process_message(body: bytes, webhook_timeout: float, auth_secret: str) -> None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 파싱 실패: {exc}") from exc

    try:
        req = ContentGenerateRequest.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"요청 스키마 검증 실패: {exc}") from exc

    selection = select_keywords_for_request(req)
    post_keyword_webhook(req, selection, timeout=webhook_timeout, auth_secret=auth_secret)


def run_keyword_worker() -> None:
    _load_env()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    rabbitmq_url = _get_env("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    queue_name = _get_env("CONTENT_GENERATE_QUEUE", "content-generate-queue")
    webhook_timeout = float(_get_env("WEBHOOK_TIMEOUT_SECONDS", "10") or 10)
    keyword_webhook_secret = _get_env("KEYWORD_SELECT_WEBHOOK_SECRET")

    params = pika.URLParameters(rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    logger.info("Keyword worker started. queue=%s", queue_name)

    def _handle(ch, method, properties, body):
        try:
            process_message(body, webhook_timeout=webhook_timeout, auth_secret=keyword_webhook_secret)
        except Exception as exc:
            logger.error("메시지 처리 실패, nack: %s", exc, exc_info=False)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name, on_message_callback=_handle, auto_ack=False)

    def _graceful_stop(signum, frame):
        logger.info("중단 신호 수신(%s), 종료합니다.", signum)
        channel.stop_consuming()

    signal.signal(signal.SIGTERM, _graceful_stop)
    signal.signal(signal.SIGINT, _graceful_stop)

    try:
        channel.start_consuming()
    finally:
        try:
            channel.close()
        finally:
            connection.close()


if __name__ == "__main__":
    run_keyword_worker()
