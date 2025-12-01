# Blog Upload Worker

RabbitMQ에서 `blog-upload-queue` 큐를 소비하여 `blog_upload_module` 모듈을 직접 호출하는 파이썬 워커입니다. Spring Boot에서 `BlogUploadRequest` 를 발행하면 워커가 네이버/티스토리 업로드를 수행하고, 필요 시 웹훅으로 결과를 전달합니다.

## 실행 방법

1. 루트에서 `pip install -e .[worker]` 로 패키지를 설치합니다. (설치 방법은 상위 `README.md` 의 "설치" 절을 참고하세요.)
2. 환경 변수를 설정합니다. 기본값은 도커 컴포즈 설정을 따르므로, 로컬에서 바로 실행하면 `guest/guest @ localhost:5672` 로 연결됩니다.
   ```bash
   export RABBITMQ_HOST=localhost
   export RABBITMQ_PORT=5672
   export RABBITMQ_USERNAME=guest
   export RABBITMQ_PASSWORD=guest
   export RABBITMQ_BLOG_QUEUE=blog-upload-queue
   export RABBITMQ_PREFETCH=1
   ```

3. 워커를 실행합니다. 설치 시 자동으로 `blog-worker` 콘솔 스크립트가 생성되며, 필요하면 모듈 실행 방식(`python -m blog_worker.run_worker`)을 그대로 사용해도 됩니다.
   ```bash
   blog-worker
   ```

## 메시지 포맷

Spring Boot 의 `BlogUploadRequest` JSON을 그대로 사용합니다.
```json
{
  "workId": 123,
  "blogType": "NAVER",
  "title": "제목",
  "content": "<p>본문</p>",
  "blogId": "user@example.com",
  "blogPassword": "password",
  "blogUrl": "https://blog.naver.com/user",
  "webhookUrl": "https://backend/api/webhook",       // (선택)
  "webhookToken": "Bearer abc123"                     // (선택)
}
```

워커는 `blogType` 에 따라 `blog_upload_module.upload_to_naver_blog` 또는 `upload_to_tistory_blog` 를 호출하고, `UploadResult` 의 `posting_url` 과 `status` 를 로그/웹훅으로 남깁니다.

## 커스터마이징

- `blog_worker/config.py` 에서 RabbitMQ 접속 정보를 환경 변수 기반으로 로딩합니다.
- `blog_worker/job_executor.py` 에서 `headless` 옵션이나 `wait_time` 을 조정할 수 있습니다.
- 웹훅 전송을 사용하려면 메시지에 `webhookUrl`/`webhookToken` 을 포함시키면 됩니다. (미지정 시 전송하지 않습니다.)
- 로깅 경로나 파일명은 `WORKER_LOG_DIR`, `WORKER_LOG_FILE`, `WORKER_LOG_LEVEL` 환경 변수로 제어하며 `blog_upload_module` 의 공통 로거 설정을 그대로 재사용합니다.
