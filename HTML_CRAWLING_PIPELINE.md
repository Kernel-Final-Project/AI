# HTML 크롤링 파이프라인 구축 작업 기록

## 📅 작업 시작일: 2025-11-20

## 🎯 목표
다양한 쇼핑몰 사이트(무신사, ssadagu 등)에서 URL을 입력받아 자동으로 SSR/CSR을 판별하고, 적절한 방법으로 HTML을 추출하는 범용 크롤링 파이프라인 구축

## 📋 작업 체크리스트

### Phase 1: SSR/CSR 판별 기능
- [ ] SSR 여부 확인 (requests로 HTML 즉시 로딩 가능 여부)
- [ ] CSR 여부 확인 (<script> 기반 데이터 로딩 여부)
- [ ] 판별 결과 리포트 생성

### Phase 2: HTML 추출 기능
- [ ] 자동 방법 선택 로직 (SSR → requests, CSR → Selenium)
- [ ] requests 기반 HTML 추출
- [ ] Selenium 기반 HTML 추출
- [ ] 통합 HTML 추출 함수

### Phase 3: 테스트 및 검증
- [ ] 다양한 사이트 테스트 (무신사, ssadagu 등)
- [ ] 에러 핸들링
- [ ] 로깅 추가

## 🏗️ 모듈 구조

```
scraper/
  ├── __init__.py
  ├── ssr_csr_checker.py    # SSR/CSR 판별 모듈
  ├── html_extractor.py     # HTML 추출 모듈 (자동 방법 선택)
  └── utils.py              # 유틸리티 함수들
```

## 📝 작업 진행 상황

### 2025-11-20
- [x] 작업 계획 수립
- [x] MD 파일 생성
- [x] 모듈 구조 생성
  - `scraper/__init__.py` 생성
  - `scraper/ssr_csr_checker.py` 생성
  - `scraper/html_extractor.py` 생성
  - `scraper/utils.py` 생성
- [x] SSR/CSR 판별 기능 구현
  - `check_ssr_csr()` 함수 구현
  - 콘텐츠 포함 여부 확인
  - 스크립트 태그 분석
  - API 엔드포인트 탐지
  - JSON 데이터 확인
  - 판별 로직 구현 (SSR/CSR/HYBRID/UNKNOWN)
- [x] HTML 추출 기능 구현
  - `extract_html()` 함수 구현 (자동 방법 선택)
  - `_extract_with_requests()` 구현
  - `_extract_with_selenium()` 구현
  - `extract_html_with_fallback()` 구현
- [x] 테스트 스크립트 작성
  - `test_scraper.py` 생성
- [x] DOM 요소 로딩 확인 기능 개선
  - `_wait_for_dom_elements()` 헬퍼 함수 추가
  - 주요 DOM 요소 확인 (body, article, main, .content, .product, h1-h3, p 등)
  - `_extract_with_selenium()` 함수에 DOM 요소 확인 로직 추가
  - 커스텀 선택자 지원 기능 추가

