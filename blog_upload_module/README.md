# blog_upload_module

블로그 자동 업로드 기능만 별도로 떼어낸 경량 패키지입니다.  
`pyproject.toml` 기반으로 구성되어 있으므로 `pip install -e .` 만으로 CLI, 모듈, RabbitMQ 워커를 모두 사용할 수 있습니다.

## 설치

1. 가상환경을 만든 뒤 활성화합니다. 저장소 루트 바깥 (예: `~/venvs/blog-upload-module`) 에 가상환경을 만드는 것을 권장합니다.
   ```bash
   python3 -m venv ~/venvs/blog-upload-module
   source ~/venvs/blog-upload-module/bin/activate
   ```
   (불가피하게 루트에 `.venv/` 를 둘 경우 `.gitignore` 로 이미 제외되어 있으므로 그대로 사용해도 됩니다.)
2. 패키지를 편집 모드로 설치합니다.
   ```bash
   pip install -e .
   # RabbitMQ 워커까지 함께 쓰려면
   pip install -e .[worker]
   ```

## CLI 사용

실행 시 모든 계정/환경 정보를 CLI 옵션으로 전달합니다. `blog-upload-module` 엔트리 포인트(또는 `python -m blog_upload_module.run_posting`)를 사용할 수 있습니다.
   - 네이버 필수 옵션: `--naver-id`, `--naver-pw`, `--naver-blog-url`
   - 티스토리 필수 옵션: `--tistory-blog-url`, `--kakao-id`, `--kakao-password`
   - 공통 옵션: `--headless`(창 없이 실행), `--wait-time`, `--log-level`
   - 콘텐츠 옵션: `--title`, `--body`, `--body-file`, `--skip-confirm`

샘플 콘텐츠로 테스트:
```bash
blog-upload-module \
  --platform naver \
  --naver-id your_id \
  --naver-pw your_password \
  --naver-blog-url https://blog.naver.com/your_blog \
  --title "테스트 제목" \
  --body "<p>본문</p>" \
  --skip-confirm

blog-upload-module \
  --platform tistory \
  --tistory-blog-url https://your-blog.tistory.com \
  --kakao-id your_kakao_id \
  --kakao-password your_kakao_pw \
  --title "테스트 제목" \
  --body "일반 텍스트도 가능합니다." \
  --skip-confirm
```
옵션:
- `--title`: 업로드할 제목 지정
- `--body`: 본문 문자열 직접 입력 (HTML 가능)
- `--body-file`: 파일에서 본문 읽기
- `--skip-confirm`: 업로드 전 사용자 확인 생략
- `--headless`: GUI 없이 실행
- `--wait-time`: WebDriverWait 기본 초 단위
- `--log-level`: `INFO`, `DEBUG` 등 로그 레벨
- `--work-id`: 백엔드 워크 테이블 ID를 로그/웹훅에 포함
- `--webhook-url`: 업로드 결과를 POST할 엔드포인트
- `--webhook-token`: 웹훅 X-WEBHOOK-SECRET 헤더 값
- `--webhook-timeout`: 웹훅 HTTP 요청 타임아웃(초). 기본값 5
- `--emit-json`: 업로드 결과를 JSON 형태로 stdout에 출력

로그는 기본적으로 **현재 작업 디렉터리의 `logs/`** 에 기록되며, `BLOG_UPLOAD_MODULE_LOG_DIR` 환경 변수를 지정하면 다른 경로로 보낼 수 있습니다. 워커는 `WORKER_LOG_DIR`, `WORKER_LOG_FILE`, `WORKER_LOG_LEVEL` 로 동일한 로거 헬퍼를 재사용합니다.

### 웹훅 연동

RabbitMQ 워커나 Spring Boot 백엔드와 연동할 때는 `--work-id` 와 `--webhook-url` 을 함께 지정합니다.  
업로드가 끝나면 `"workId"`, `"status"`, `"postingUrl"` 등이 포함된 JSON을 웹훅으로 전송하며, 동일한 헬퍼를 워커도 사용합니다.  
동시에 `--emit-json` 을 켜면 동일한 페이로드를 CLI 표준출력에서도 확인할 수 있습니다.

## 모듈 사용

파이썬 코드에서 직접 호출할 수도 있습니다.
```python
from blog_upload_module import UploadResult, upload_to_naver_blog, upload_to_tistory_blog

payload = {"title": "제목", "body_html": "<h2>본문</h2>"}
naver_result: UploadResult = upload_to_naver_blog(
    payload,
    naver_id="your_id",
    naver_pw="your_password",
    blog_url="https://blog.naver.com/your_blog",
)
print(naver_result.posting_url)

tistory_result = upload_to_tistory_blog(
    payload,
    blog_url="https://your-blog.tistory.com",
    kakao_id="your_kakao_id",
    kakao_pw="your_kakao_pw",
)
print(tistory_result.status)
```

콘텐츠 딕셔너리는 `title` 과 `body_html` (또는 `content`) 키를 포함하면 됩니다.

## RabbitMQ 워커

`blog_worker` 패키지는 `pip install -e .[worker]` 이후 `blog-worker` (또는 `python -m blog_worker.run_worker`) 로 실행할 수 있습니다.  
상세 사용법은 `src/blog_worker/README.md` 를 참고하세요. 워커 역시 `blog_upload_module` 패키지의 업로더/웹훅/로거 헬퍼를 그대로 사용하도록 정리되어 있습니다.
