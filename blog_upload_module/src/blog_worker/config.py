"""
Configuration helpers for the RabbitMQ worker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RabbitSettings:
    host: str
    port: int
    username: str
    password: str
    queue: str
    prefetch: int
    use_ssl: bool


def load_rabbit_settings() -> RabbitSettings:
    return RabbitSettings(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        username=os.getenv("RABBITMQ_USERNAME", "guest"),
        password=os.getenv("RABBITMQ_PASSWORD", "guest"),
        queue=os.getenv("RABBITMQ_BLOG_QUEUE", "blog-upload-queue"),
        prefetch=int(os.getenv("RABBITMQ_PREFETCH", "1")),
        use_ssl=os.getenv("RABBITMQ_USE_SSL", "false").lower() in {"1", "true", "yes"},
    )
