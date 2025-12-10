from __future__ import annotations

import logging
import os
import signal
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from keywordCrawler.services import crawl_keywords_to_list
from select_keyword.selector import SelectionResult, select_from_lists
from worker.common.models import ContentGenerateRequest, KeywordSelectPayload, UsedProductInfo, now_iso
from worker.common.mq import consume
from worker.common.webhook import post_webhook

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKER_ROOT = Path(__file__).resolve().parents[1]
ENV_PATHS = [
    REPO_ROOT / ".env",
    WORKER_ROOT / ".env",
]


def _load_env() -> None:
    for env_path in ENV_PATHS:
        if env_path.is_file():
            load_dotenv(env_path, override=False)


def _get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def _build_exclude_list(req: ContentGenerateRequest) -> List[str]:
    excludes: List[str] = []
    excludes.extend([kw for kw in (req.recentTrendKeywords or []) if kw])

    for item in req.recentlyUsedProducts or []:
        if isinstance(item, str):
            token = item.strip()
            if token:
                excludes.append(token)
            continue
        if isinstance(item, UsedProductInfo):
            if item.productUrl:
                excludes.append(item.productUrl)
            if item.name:
                excludes.append(item.name)
    return excludes


def select_keywords_for_request(req: ContentGenerateRequest) -> SelectionResult:
    candidates = crawl_keywords_to_list(
        req.trendCategory.category1,
        req.trendCategory.category2,
        req.trendCategory.category3,
        headless=True,
    )

    selection = select_from_lists(
        candidates,
        exclude=_build_exclude_list(req),
        top_n=1,
    )
    return selection[0]


def process_message(req: ContentGenerateRequest, webhook_secret: str | None, webhook_timeout: float) -> None:
    selection = select_keywords_for_request(req)
    payload = KeywordSelectPayload(
        workId=req.workId,
        keyword=selection.keyword,
        success=True,
        message=selection.reason,
        startedAt=now_iso(),
        completedAt=now_iso(),
    ).model_dump()
    post_webhook(
        req.webhookUrls.keywordSelect,
        secret=webhook_secret,
        payload=payload,
        timeout=webhook_timeout,
    )


def run_keyword_worker() -> None:
    _load_env()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    mq_url = _get_env("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    queue_name = _get_env("CONTENT_GENERATE_QUEUE", "content-generate-queue")
    webhook_timeout = float(_get_env("WEBHOOK_TIMEOUT_SECONDS", "10") or 10)
    keyword_webhook_secret = _get_env("KEYWORD_SELECT_WEBHOOK_SECRET")

    logger.info("Keyword worker started. queue=%s", queue_name)

    # Graceful stop support
    def _stop_consume(signum, frame):
        logger.info("중단 신호 수신(%s), 종료합니다.", signum)
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, _stop_consume)
    signal.signal(signal.SIGINT, _stop_consume)

    def _callback(body: dict) -> None:
        req = ContentGenerateRequest.model_validate(body)
        process_message(req, webhook_secret=keyword_webhook_secret, webhook_timeout=webhook_timeout)

    consume(queue_name, _callback, mq_url)


if __name__ == "__main__":
    run_keyword_worker()
