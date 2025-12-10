from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pika
from dotenv import load_dotenv

from worker.common.models import (
    ContentGenerateRequest,
    ProductInfo,
    TrendCategory,
    UsedProductInfo,
    WebhookUrls,
)


def load_env() -> None:
    for env_path in [
        Path(__file__).resolve().parents[0] / ".env",  # worker/.env
        Path(__file__).resolve().parents[1] / ".env",  # repo/.env
    ]:
        if env_path.is_file():
            load_dotenv(env_path, override=False)


def build_sample_payload() -> dict:
    work_id = int(datetime.utcnow().timestamp())
    sample = ContentGenerateRequest(
        workId=work_id,
        hasCrawledItems=False,
        recentTrendKeywords=["예시 키워드1", "예시 키워드2"],
        crawledProducts=[
            ProductInfo(productId="123", name="테스트 상품", price=19900, productUrl="https://example.com/item/123"),
        ],
        # 백엔드 호환을 위해 문자열 리스트로 전달
        recentlyUsedProducts=[
            "https://example.com/item/old",
            "지난 상품",
        ],
        trendCategory=TrendCategory(category1="패션의류", category2="여성의류", category3="맨투맨"),
        siteUrl="https://example.com",
        webhookUrls=WebhookUrls(
            keywordSelect=os.getenv("KEYWORD_SELECT_WEBHOOK_URL", "http://localhost:8000/webhook/keyword"),
            productSelect=os.getenv("PRODUCT_SELECT_WEBHOOK_URL"),
            contentGenerate=os.getenv("CONTENT_GENERATE_WEBHOOK_URL"),
        ),
    )
    return sample.model_dump()


def main() -> None:
    load_env()
    mq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    queue_name = os.getenv("CONTENT_GENERATE_QUEUE", "content-generate-queue")

    payload = build_sample_payload()
    connection = pika.BlockingConnection(pika.URLParameters(mq_url))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    print(f"sent test message: workId={payload['workId']}")
    connection.close()


if __name__ == "__main__":
    main()
