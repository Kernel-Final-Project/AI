"""
RabbitMQ consumer for blog upload jobs.
"""

from __future__ import annotations

import json
import threading
import pika
from pika.adapters.blocking_connection import BlockingChannel

from blog_upload_module import UploadResult
from blog_upload_module.webhook import notify_upload_result

from .config import load_rabbit_settings
from .job_executor import execute_blog_upload
from .logger import logger
from .models import BlogUploadRequest


class BlogUploadConsumer:
    def __init__(self) -> None:
        self.settings = load_rabbit_settings()
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None
        self._lock = threading.Lock()

    def connect(self) -> None:
        with self._lock:
            if self._connection and self._connection.is_open:
                return
            credentials = pika.PlainCredentials(
                self.settings.username, self.settings.password
            )

            # SSL 설정
            if self.settings.use_ssl:
                context = ssl.create_default_context()
                ssl_options = pika.SSLOptions(context)
            else:
                ssl_options = None

            parameters = pika.ConnectionParameters(
                host=self.settings.host,
                port=self.settings.port,
                credentials=credentials,
                heartbeat=30,
                ssl_options=ssl_options,
            )
            logger.info(
                "RabbitMQ 연결 시도 host=%s port=%s queue=%s",
                self.settings.host,
                self.settings.port,
                self.settings.queue,
            )
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            self._channel.basic_qos(prefetch_count=self.settings.prefetch)
            self._channel.queue_declare(queue=self.settings.queue, durable=True)

    def start(self) -> None:
        self.connect()
        assert self._channel is not None
        self._channel.basic_consume(
            queue=self.settings.queue, on_message_callback=self._on_message
        )
        logger.info("RabbitMQ 소비 시작 (queue=%s)", self.settings.queue)
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("소비 종료 요청 수신")
        finally:
            self.stop()

    def stop(self) -> None:
        if self._channel and self._channel.is_open:
            self._channel.close()
        if self._connection and self._connection.is_open:
            self._connection.close()

    def _on_message(self, ch: BlockingChannel, method, properties, body: bytes) -> None:
        logger.info("메시지 수신: delivery_tag=%s", method.delivery_tag)
        try:
            request = BlogUploadRequest.from_json(body)
            result = execute_blog_upload(request)
            _notify_webhook(request, result)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except json.JSONDecodeError as exc:
            logger.error("메시지 JSON 파싱 실패: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as exc:  # noqa: BLE001
            logger.exception("업로드 처리 중 오류: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def run_consumer() -> None:
    consumer = BlogUploadConsumer()
    consumer.start()


def _notify_webhook(request: BlogUploadRequest, result: UploadResult) -> None:
    work_id = str(request.work_id) if request.work_id is not None else None
    notify_upload_result(
        result,
        webhook_url=request.webhook_url,
        token=request.webhook_token,
        timeout=5,
        work_id=work_id,
        log=logger,
    )
