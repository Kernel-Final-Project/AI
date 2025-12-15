"""
설정 관리 모듈
"""
import os
from typing import Optional

# RabbitMQ 설정
RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")

# 큐 이름
CRAWLING_REQUEST_QUEUE: str = "crawling-request-queue"
CRAWLING_RESPONSE_QUEUE: str = "crawling-response-queue"

# FastAPI 설정
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# Spring 서버 설정 (결과 전송용)
SPRING_SERVER_URL: str = os.getenv("SPRING_SERVER_URL", "http://localhost:8080/api/v1/crawling/products")

# RabbitMQ 연결 URL 생성
def get_rabbitmq_url() -> str:
    """RabbitMQ 연결 URL 생성"""
    return f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}{RABBITMQ_VHOST}"
