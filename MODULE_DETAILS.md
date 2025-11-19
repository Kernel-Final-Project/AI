# 모듈 상세 설계

## ① 트렌드 데이터 수집 모듈 (trend_collector.py)

### 기능
1. **Google Trends 크롤링**
   - pytrends 라이브러리 활용 또는 Selenium으로 직접 크롤링
   - 실시간 트렌드 키워드 수집
   - 지역: 한국 (KR)

2. **관련 검색어/주제 확장**
   - 각 트렌드 키워드의 관련 검색어 수집
   - 관련 주제(Related Topics) 수집
   - 검색어 네트워크 확장

3. **키워드 필터링 규칙**
   - 상품명으로 적합한 키워드만 선별
   - 불필요한 키워드 제거 (인물명, 이벤트명 등)
   - 최소 검색량 기준 적용

4. **키워드 중복 제거**
   - 유사 키워드 통합
   - 동의어 처리

5. **Top 30~50개 자동 선정**
   - 트렌드 점수 기반 정렬
   - 최종 1개 랜덤 선택

### 출력 형식
```json
{
  "selected_keyword": "아이패드 프로",
  "trend_score": 95,
  "related_keywords": ["아이패드", "태블릿", "애플"],
  "collection_date": "2025-11-17"
}
```

---

## ② AI 콘텐츠 생성 엔진

### 2-1) 제목 생성 (title_generator.py)

**목표:** SEO 최적화 + 높은 CTR

**생성 규칙:**
- 호기심 유발 문구 포함
- 숫자/통계 활용
- 감정어 포함
- 예시: "부모들이 미친 듯 찾는 ○○, 왜 갑자기 인기일까?"

**입력:**
- 선택된 키워드
- 상품 정보

**출력:**
- SEO 최적화된 제목 3-5개 후보
- 최종 선택된 제목 1개

---

### 2-2) 아웃라인 생성 (outline_generator.py)

**목표:** 본문 5~7개 섹션 자동 생성

**섹션 구조:**
1. 도입부 (소개)
2. 상품 특징/장점
3. 사용 후기/리뷰 느낌
4. 추천 대상
5. 구매 팁/주의사항
6. 마무리/결론
7. (선택) FAQ

**입력:**
- 선택된 키워드
- 상품 정보
- 제목

**출력:**
```json
{
  "outline": [
    {"section": 1, "title": "도입부", "description": "..."},
    {"section": 2, "title": "상품 특징", "description": "..."},
    ...
  ]
}
```

---

### 2-3) 본문 생성 (body_generator.py)

**목표:** 키워드 기반 1,000~1,500자 블로그 글 생성

**요구사항:**
- 자연스럽고 광고 같지 않은 문체
- SEO 고려한 h2, h3 구조
- 키워드 자연스럽게 배치
- 읽기 쉬운 문단 구성

**입력:**
- 아웃라인
- 상품 정보
- 키워드

**출력:**
- HTML 형식의 본문 (h2, h3 태그 포함)
- 마크다운 형식 (선택)

---

### 2-4) 이미지 생성 (image_generator.py) - 선택

**목표:** 상품 리뷰 느낌 이미지 생성

**방법:**
- DALL·E API 사용
- 프롬프트: "상품 리뷰 느낌의 자연스러운 제품 사진, 깔끔한 배경"
- 대안: 미드저니 API (실사 느낌 필요 시)

**입력:**
- 상품명
- 상품 카테고리

**출력:**
- 이미지 URL 또는 파일 경로

---

### 2-5) 최종 텍스트 포맷팅 (formatter.py)

**목표:** 백엔드가 블로그에 넣기 편하게 포맷 제공

**포맷:**
- HTML 형식
- h2, h3 태그 포함
- 이미지 태그 포함
- 메타데이터 포함

**출력 형식:**
```json
{
  "title": "생성된 제목",
  "content_html": "<h2>섹션1</h2><p>내용...</p>",
  "images": ["image_url1", "image_url2"],
  "keywords": ["키워드1", "키워드2"],
  "created_at": "2025-11-17T10:00:00",
  "metadata": {
    "word_count": 1200,
    "seo_score": 85
  }
}
```

---

## ③ ssadagu.kr 상품 수집 (product_collector.py)

### 기능
1. 선택된 키워드로 ssadagu.kr 검색
2. 상품 제목 수집
3. 상품 정보 추출 (가격, 이미지, 링크 등)
4. 상품 정보를 콘텐츠 생성에 활용

### 출력 형식
```json
{
  "products": [
    {
      "title": "상품명",
      "price": "가격",
      "image_url": "이미지URL",
      "product_url": "상품링크",
      "description": "상품설명"
    }
  ],
  "total_count": 10
}
```

---

## ④ 결과 저장 (storage/)

### data_storage.py
- `data/` 루트 하위에 `trends/`, `products/`, `posts/`, `logs/` 디렉토리 자동 생성
- 트렌드/상품/포스트/실행 로그 데이터를 공통 포맷(`{"metadata": {...}, "items": [...]}`)으로 저장
- 파일명은 `trends_20251118_120000.json` 형태로 자동 생성 (필요 시 직접 지정 가능)
- 메타데이터에 `count`, `saved_at`, `run_id`, `strategy`, `keyword` 등의 정보를 포함해 이력 관리
- `keyword_history.json`으로 최근 선택 키워드 기록 관리 (기본 50개, `StorageConfig.keyword_history_limit`으로 조정 가능)
- 히스토리 파일이 손상되면 자동으로 복구하며, 저장 시 최신 기록만 유지
- `generate_run_id()`로 파이프라인 실행별 고유 ID 부여
- `load_latest_trends()`, `load_latest_products()`, `load_latest_post()`, `load_recent_run_logs()`로 최근 저장 데이터를 손쉽게 조회

### file_manager.py
- JSON/HTML 저장 유틸리티
- `data_storage`가 내부적으로 재사용

### db_handler.py (선택)
- SQLite 또는 PostgreSQL에 저장 (향후 필요 시 구현)

---

## ⑤ AI 스케줄러 (scheduler.py)

- `scheduler/main_scheduler.py`에서 전체 파이프라인 실행
- 08:00 실행을 기본값으로 하고 `SCHEDULE_TIME` 환경변수로 조정 가능
- 1단계 트렌드 수집 시 `collect_and_store_trends()` 호출 → 결과가 즉시 `data/trends/`에 저장
- 키워드 선택 시 `storage.load_keyword_history()`로 최근 사용 내역을 불러와 중복 선택을 방지하고, 선택 결과는 `save_run_log()`와 `save_keyword_history()`로 기록
- `KEYWORD_SELECTION_WEIGHTED=true` 설정 시 트렌드 점수를 기반으로 가중치 랜덤을 적용해 인기 키워드 우선 선택 가능
- 각 실행마다 `run_id`를 생성해 모든 저장/로그에 공통 메타데이터로 기록
- ssadagu, 콘텐츠 생성, 블로그 업로드는 현재 스텁으로 연결되어 있으며 추후 실제 모듈을 바인딩 예정

### 기능
- 매일 오전 10시에 자동 실행
- 전체 파이프라인 실행:
  1. 트렌드 크롤링
  2. 상품 수집
  3. 콘텐츠 생성
  4. 결과 저장

### 실행 흐름
```
10:00 → 트렌드 수집 → 상품 수집 → 콘텐츠 생성 → 저장 → 완료
```

### 로깅
- 각 단계별 로그 기록
- 에러 발생 시 알림 (선택)
