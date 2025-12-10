from __future__ import annotations

import json
import logging
import time
from typing import Callable

import pika

logger = logging.getLogger(__name__)

CallbackType = Callable[[dict], None]


def connect_mq(mq_url: str, *, retries: int = 3, delay: float = 2.0) -> pika.BlockingConnection:
    """RabbitMQ BlockingConnection을 생성한다."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            params = pika.URLParameters(mq_url)
            return pika.BlockingConnection(params)
        except Exception as exc:  # pragma: no cover - 연결 실패 대비
            last_exc = exc
            logger.warning("MQ 연결 실패 (%s/%s): %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError("RabbitMQ 연결에 실패했습니다.") from last_exc


def consume(queue: str, callback: CallbackType, mq_url: str, *, prefetch_count: int = 1) -> None:
    """
    JSON 메시지를 소비하는 공통 컨슈머.
    callback은 body(dict)를 인자로 받는다.
    """
    while True:
        connection = None
        channel = None
        try:
            connection = connect_mq(mq_url)
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)
            channel.basic_qos(prefetch_count=prefetch_count)
            logger.info("MQ consume start: queue=%s", queue)

            def _on_message(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception as exc:
                    logger.error("메시지 JSON 파싱 실패, nack: %s", exc, exc_info=False)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                    return

                try:
                    callback(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as exc:  # pragma: no cover - 보호적 핸들링
                    logger.error("메시지 처리 실패, nack: %s", exc, exc_info=False)
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(queue=queue, on_message_callback=_on_message, auto_ack=False)
            channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("컨슈머 중단 신호 수신, 종료합니다.")
            break
        except Exception as exc:  # pragma: no cover - 재연결 루프
            logger.error("consume 루프 예외, 재시도합니다: %s", exc, exc_info=False)
            time.sleep(2.0)
        finally:
            try:
                if channel and channel.is_open:
                    channel.close()
            finally:
                if connection and connection.is_open:
                    connection.close()
