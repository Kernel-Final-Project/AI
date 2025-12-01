## AI Integration Pipeline

크롤링한 인기 키워드에서 가장 의미 있는 키워드와 상품을 고르고, GPT로 블로그 콘텐츠까지 자동 작성하는 파이프라인입니다. 각 단계는 개별 CLI 모듈로 분리되어 있으며, `run_pipeline.py`로 한 번에 실행할 수도 있습니다.

### 구성 요소
- `keywordCrawler/`: Selenium으로 Itemscout 카테고리를 순회하며 `keywords.csv`를 추출합니다.
- `select_keyword/`: OpenAI GPT를 호출해 중복/불용어를 제외한 키워드 중 1개만 선정합니다.
- `select_product/`: 상품 리스트(`product_list.csv`)에서 과거 선정 이력을 제외하고, 선택된 키워드와 가장 잘 맞는 상품을 GPT로 고릅니다.
- `generate_content/`: 최종 상품 정보를 바탕으로 블로그용 제목과 Markdown 본문을 생성합니다.

### 준비 사항
1. Python 3.10+ 환경과 필요한 라이브러리 설치 (예: `pip install -r keywordCrawler/requirements.txt` + `pip install openai python-dotenv`).
2. Chrome/Chromedriver 또는 Selenium이 접근 가능한 브라우저 준비.
3. OpenAI API Key를 환경 변수 `OPENAI_API_KEY` 또는 루트 `.env`에 저장.
4. 데이터 파일 작성:
   - `product_list.csv`: 후보 상품 목록 (최소한 상품명 컬럼 필요).
   - `past_selected_product_list.csv`: 다시 고르면 안 되는 상품명 목록 (없으면 빈 파일 허용).
   - `excep.csv`: 제외할 키워드 목록 (필요 시).

### 빠르게 실행하기
```bash
OPENAI_API_KEY=sk-... \
python run_pipeline.py \
  --c1 패션의류 \
  --c2 여성의류 \
  --c3 맨투맨 \
  --product-list product_list.csv \
  --past-products past_selected_product_list.csv
```

- 로그는 `logs/pipeline-YYYYmmdd-HHMMSS.log` 파일로 모입니다.
- 최종 산출물은 `outputs/pipeline_result.json` 한 파일에 키워드/상품/콘텐츠 정보가 모두 포함됩니다.

`pipeline_result.json` 구조 예시:
```json
{
  "metadata": { "generated_at": "...", "log_file": "logs/pipeline-....log" },
  "keywords": { "candidates": [...], "selected": {...} },
  "product": {...},
  "content": { "title": "...", "content": "마크다운 본문", "raw_response": "..." }
}
```

### 모듈별 단독 실행
- **키워드 크롤링**
  ```bash
  python -m keywordCrawler --c1 패션의류 --c2 여성의류 --c3 맨투맨 -o keywordCrawler/keywords.csv --headless
  ```
- **키워드 선택**
  ```bash
  --keywords-csv keywpython -m select_keyword ordCrawler/keywords.csv --exclude-csv excep.csv --output selected_keyword.json
  ```
- **상품 선택**
  ```bash
  python -m select_product \
    --products-csv product_list.csv \
    --selected-keyword-file selected_keyword.json \
    --exclude-csv past_selected_product_list.csv \
    --output selected_product.json
  ```
- **콘텐츠 생성**
  ```bash
  python -m generate_content --selection-file selected_product.json --output generated_content.json
  ```

필요에 따라 `--format text`를 사용하면 콘솔/파일에 Markdown 본문만 출력할 수 있습니다.

### 팁
- 파이프라인 실행 전 `product_list.csv`와 `past_selected_product_list.csv`를 최신 상태로 유지하세요.
- `run_pipeline.py`는 Selenium 단계부터 GPT 호출까지 순차적으로 실행하므로 중간에 실패하면 해당 단계 이후만 다시 실행하면 됩니다 (예: `outputs/keywords.csv`가 있으면 `--skip-crawl` 옵션을 추가하도록 확장 가능).
- `.env` 파일을 루트에 두면 모든 모듈이 동일한 OpenAI API Key를 자동으로 공유합니다.
