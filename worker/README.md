# Python Worker 인프라

키워드/상품/콘텐츠 워커를 위한 공통 구조입니다. 현재 키워드 워커만 동작하며, 상품/콘텐츠 워커는 스켈레톤으로 추가되어 있습니다.

## 폴더 구조
```
worker/
  common/                 # MQ, 웹훅, Pydantic 모델
  workers/
    keyword_worker.py     # 키워드 워커 엔트리포인트(실제 구현)
    product_worker.py     # 상품 워커 스켈레톤
    content_worker.py     # 콘텐츠 워커 스켈레톤
  send_test_message.py    # 테스트 메시지 퍼블리셔
  requirements.txt        # 워커 전용 의존성
```

## 각 워커/유틸 역할
- `common/mq.py`: RabbitMQ 연결/consume 공통화, JSON 파싱+ack/nack.
- `common/webhook.py`: Authorization 헤더 포함 웹훅 POST, 2xx 확인, JSON/빈 응답 처리.
- `common/models.py`: ContentGenerateRequest 등 Pydantic 모델 정의.
- `workers/keyword_worker.py`: 크롤링→키워드 선택→키워드 웹훅 호출. 최근 키워드와 사용 상품(이름/URL)까지 제외 목록에 반영.
- `workers/product_worker.py`, `workers/content_worker.py`: 향후 구현용 스켈레톤.
- `send_test_message.py`: 샘플 ContentGenerateRequest를 큐에 publish.

## 환경 변수 (.env 예시)
```
OPENAI_API_KEY=sk-...
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
CONTENT_GENERATE_QUEUE=content-generate-queue
KEYWORD_SELECT_WEBHOOK_SECRET=secret-token
WEBHOOK_TIMEOUT_SECONDS=10
# optional 테스트용 웹훅 URL
KEYWORD_SELECT_WEBHOOK_URL=http://localhost:8000/webhook/keyword
```

## 설치
```
python -m venv venv
source venv/bin/activate  # 또는 venv\\Scripts\\activate
pip install -r worker/requirements.txt
```

## 실행
- 키워드 워커: `python -m worker.workers.keyword_worker`
  - MQ: `RABBITMQ_URL`, `CONTENT_GENERATE_QUEUE`
  - 웹훅: `KEYWORD_SELECT_WEBHOOK_SECRET`, `WEBHOOK_TIMEOUT_SECONDS`
- 테스트 메시지 발행: `python worker/send_test_message.py`
  - env 기반으로 `CONTENT_GENERATE_QUEUE`에 샘플 메시지를 publish합니다.

## 메시지 스키마 예시 (ContentGenerateRequest)
```json
{
  "workId": 123,
  "hasCrawledItems": false,
  "recentTrendKeywords": ["예시 키워드1", "예시 키워드2"],
  "crawledProducts": [
    {"productId": "123", "name": "테스트 상품", "price": 19900, "productUrl": "https://example.com/item/123"}
  ],
  "recentlyUsedProducts": [
    "https://example.com/item/old",
    "지난 상품"
  ],
  "trendCategory": {"category1": "패션의류", "category2": "여성의류", "category3": "맨투맨"},
  "siteUrl": "https://example.com",
  "webhookUrls": {
    "keywordSelect": "http://localhost:8000/webhook/keyword",
    "productSelect": null,
    "contentGenerate": null
  }
}
```

## 동작 개요
- `worker.common.mq.consume`: RabbitMQ 연결/consume 공통화, JSON 파싱, 성공 시 ack, 실패 시 nack(requeue=False).
- `worker.common.webhook.post_webhook`: Authorization 헤더 자동 적용, 2xx가 아니면 예외.
- `worker.workers.keyword_worker`: Itemscout 크롤링 → GPT 키워드 선택 → 키워드 웹훅 호출. 최근 키워드와 사용한 상품(이름/URL)로 제외 목록을 구성합니다.
- `worker.workers.product_worker` / `content_worker`: 이후 구현을 위한 스켈레톤.

## 주의
- 백엔드 호환을 위해 `recentlyUsedProducts`는 문자열 리스트(URL/상품명 등)로 보내는 것을 권장합니다.
