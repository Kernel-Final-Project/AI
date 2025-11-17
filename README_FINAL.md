# 📊 AI Trend-Based Blog Automation Project

**Google Trends → AI Content Generation → Naver/Tistory Auto Posting**

> 🎓 **기술 검증 및 학습 목적의 포트폴리오 프로젝트**  
> 본 프로젝트는 크롤링, AI, 자동화 기술의 통합 구현 가능성을 탐구하는 PoC(Proof of Concept) 수준의 시스템입니다.

---

## 📌 Overview

이 프로젝트는 Google Trends 기반으로 **'오늘 뜨는 이슈 상품 50개'**를 자동 수집하고,  
OpenAI GPT를 활용해 블로그용 고품질 콘텐츠를 자동 생성한 뒤,  
**Selenium을 이용해 네이버 블로그와 티스토리에 자동 업로드**하는  
**완전 자동화 콘텐츠 운영 시스템(AI Blogging Automation System)**입니다.

본 프로젝트는 실제 개인/기업 블로그 자동 운영 시스템과 유사한 흐름을 가지며,  
크롤링·AI·자동화 기술을 모두 활용하는 **실전형 포트폴리오 프로젝트**입니다.

### 🎯 프로젝트 목표

1. **트렌드 데이터 수집**: Google Trends 기반 이슈 상품 키워드 자동 추출
2. **AI 콘텐츠 생성**: LLM을 활용한 SEO 최적화 블로그 콘텐츠 자동 생성
3. **자동 배포**: 생성된 콘텐츠를 블로그 플랫폼에 자동 업로드
4. **스케줄링**: 매일 정기적으로 콘텐츠 생성 및 배포 자동화

---

## 🚀 Key Features

### 🔍 1. Google Trends 기반 트렌드 키워드 자동 수집

- 최신 트렌드 상품 키워드 50개 자동 수집  
- Pytrends + Selenium 기반 복합 크롤링  
- 관련 검색어·관련 주제 확장  
- 불필요 키워드 필터링(연예/정치/뉴스 등)  
- 점수 기반 상위 30~50개 선별  
- 최종 1개 키워드 랜덤 선택

**기술 스택**: `pytrends`, `selenium`, `beautifulsoup4`, `pandas`

---

### ✍️ 2. AI 콘텐츠 자동 생성 (OpenAI GPT)

- **SEO 기반 제목 자동 생성**: CTR 최적화된 제목 구조
- **아웃라인 자동 생성**: h2/h3 포함 5~7개 섹션 구조
- **본문 자동 생성**: 1,000~1,500자 자연스러운 블로그 글
- **이미지 자동 생성**: DALL·E 기반 상품 리뷰 느낌 이미지 (옵션)
- **HTML 템플릿 자동 구성**: 백엔드 배포용 최종 포맷팅

**기술 스택**: `openai`, `prompt-engineering`, `html-formatter`

**프롬프트 예시**:
```python
# 제목 생성 프롬프트
"다음 키워드를 기반으로 SEO 최적화되고 호기심을 유발하는 블로그 제목을 생성하세요.
키워드: {keyword}
요구사항: 
- 감정어 포함 (미친 듯, 갑자기, 왜 등)
- 숫자/통계 활용 가능
- 30자 이내
제목 3개를 생성해주세요."
```

---

### 🛒 3. ssadagu.kr 상품 정보 수집

- 선택된 키워드로 ssadagu.kr 몰 검색
- 상품 제목, 가격, 이미지, 링크 등 정보 추출
- 수집된 상품 정보를 콘텐츠 생성에 활용

**기술 스택**: `selenium`, `beautifulsoup4`, `requests`

---

### 🚀 4. 블로그 자동 업로드 (Selenium)

**네이버 · 티스토리 모두 지원**

#### ✔ 네이버 블로그 자동 업로드

- 자동 로그인  
- 글쓰기 페이지 진입  
- HTML 본문 삽입  
- 이미지 자동 업로드  
- 제목/태그 입력  
- 자동 발행  

#### ✔ 티스토리 자동 업로드

- 자동 로그인  
- 글쓰기 페이지 진입  
- HTML 본문 삽입  
- 이미지 삽입  
- 카테고리 설정  
- 자동 발행  

> ⚠️ **기술적 참고사항**  
> 본 프로젝트는 **로컬 환경에서 GUI 모드로 Selenium 브라우저를 직접 띄우는 방식**으로 안정적으로 작동하도록 개발되었습니다.  
> CAPTCHA, 2FA, IP 차단 등의 상황에 대비한 재시도 로직과 에러 핸들링이 포함되어 있습니다.

**기술 스택**: `selenium`, `webdriver-manager`, `explicit-wait`

---

### ⏱ 5. 로컬 스케줄링 기반 자동화

- Python `schedule` 또는 `APScheduler` 사용  
- 매일 오전 10시 자동 실행  
  → 트렌드 수집 → 상품 수집 → 콘텐츠 생성 → 블로그 업로드  
- 로깅 시스템으로 작업 기록 저장  
- 에러 발생 시 재시도 및 알림 기능

**기술 스택**: `schedule`, `logging`, `retry-decorator`

---

## 🧩 System Architecture

```
┌─────────────────┐
│  Google Trends  │
└────────┬────────┘
         ▼
┌─────────────────────────────┐
│ ① Trend Collector (AI1)     │
│ - Pytrends/Selenium         │
│ - Keyword Expansion         │
│ - Keyword Filtering         │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ ③ Product Collector (AI1)   │
│ - ssadagu.kr Scraping       │
│ - Product Info Extraction   │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ ② AI Content Engine (AI2)   │
│ - Title Generator (GPT)     │
│ - Outline Generator (GPT)   │
│ - Body Generator (GPT)      │
│ - Image Generator (DALL-E)  │
│ - HTML Formatter            │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ ④ Storage Handler (AI1)     │
│ - File Handler (JSON/HTML)  │
│ - DB Handler (Optional)     │
└────────┬────────────────────┘
         ▼
┌─────────────────────────────┐
│ ⑤ Scheduler                 │
│ - Daily 10:00 AM Execution  │
│ - Pipeline Orchestration    │
└─────────────────────────────┘
```

---

## 🗂 Folder Structure

```
ai-blog-project/
│
├── src/                      # 소스 코드
│   ├── __init__.py
│   ├── main.py              # 메인 실행 파일
│   │
│   ├── agents/              # AI 에이전트 모듈
│   │   ├── __init__.py
│   │   ├── trend_collector.py      # ① 트렌드 수집 (AI1)
│   │   ├── product_collector.py    # ③ 상품 수집 (AI1)
│   │   └── content_generator.py    # ② 콘텐츠 생성 (AI2)
│   │       ├── title_generator.py
│   │       ├── outline_generator.py
│   │       ├── body_generator.py
│   │       ├── image_generator.py
│   │       └── formatter.py
│   │
│   ├── storage/             # 저장 모듈 (AI1)
│   │   ├── __init__.py
│   │   ├── db_handler.py
│   │   └── file_handler.py
│   │
│   ├── utils/               # 공통 유틸리티
│   │   ├── __init__.py
│   │   ├── config.py        # 설정 관리 (공통)
│   │   ├── logger.py         # 로깅 (공통)
│   │   └── filters.py        # 키워드 필터링 (AI1)
│   │
│   └── scheduler.py         # 스케줄러 (AI1)
│
├── config/
│   └── .env.example         # 환경변수 예시
│
├── data/                    # 데이터 저장 (gitignore)
│   ├── trends/
│   ├── products/
│   └── contents/
│
├── logs/                    # 로그 파일 (gitignore)
│
├── venv/                    # 가상환경 (gitignore)
│
├── requirements.txt         # 패키지 의존성
├── .gitignore
├── README.md
└── INTERFACE.md             # 역할 간 인터페이스 정의
```

---

## 🧪 Installation

### 1. Clone repository

```bash
git clone https://github.com/YOUR-ORG/ai-blog-project.git
cd ai-blog-project
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
# venv\Scripts\activate    # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# 블로그 계정 (선택사항 - 테스트용)
NAVER_ID=your_naver_id
NAVER_PW=your_naver_password
TISTORY_ID=your_tistory_id
TISTORY_PW=your_tistory_password

# 로깅 레벨
LOG_LEVEL=INFO
```

> 💡 `.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

---

## ▶️ Usage

### 🔍 1. 트렌드 수집 (AI1 담당)

```bash
python src/agents/trend_collector.py
```

### 🛒 2. 상품 정보 수집 (AI1 담당)

```bash
python src/agents/product_collector.py
```

### ✍️ 3. 콘텐츠 생성 (AI2 담당)

```bash
python src/agents/content_generator.py
```

### 🚀 4. 전체 파이프라인 실행

```bash
python src/main.py
```

### ⏱ 5. 스케줄러 실행 (매일 10:00 AM)

```bash
python src/scheduler.py
```

---

## 🧑‍🤝‍🧑 Team Roles & Responsibilities

### 👤 AI 1 — Trend Data & Pipeline Engineer

**담당 모듈:**
- ① 트렌드 데이터 수집 모듈
  - Google Trends 크롤링
  - 관련 검색어/주제 확장
  - 키워드 필터링 및 중복 제거
  - Top 30-50 선정 로직
- ③ ssadagu.kr 상품 수집
  - 웹 크롤링/스크래핑
  - 상품 정보 추출 및 정제
- ④ 결과 저장
  - 파일/DB 저장 로직
  - 데이터 구조 설계
- ⑤ 스케줄러
  - 전체 파이프라인 통합
  - 스케줄링 로직

**필요 스킬:**
- 웹 크롤링 (Selenium, BeautifulSoup)
- 데이터 처리 및 정제
- 파이프라인 설계

---

### 👤 AI 2 — AI Content Generation Engineer

**담당 모듈:**
- ② AI 콘텐츠 생성 엔진 전체
  - 2-1) 제목 생성 (SEO 최적화)
  - 2-2) 아웃라인 생성
  - 2-3) 본문 생성 (1,000-1,500자)
  - 2-4) 이미지 생성 (DALL-E)
  - 2-5) 최종 텍스트 포맷팅

**필요 스킬:**
- LLM API 활용 (OpenAI 등)
- 프롬프트 엔지니어링
- SEO 및 콘텐츠 최적화
- HTML 포맷팅

---

### 🤝 공통 작업

- **설정 관리** (`src/utils/config.py`, `.env`)
- **로깅 시스템** (`src/utils/logger.py`)
- **메인 실행 파일** (`src/main.py`) - 통합 테스트
- **인터페이스 정의** (`INTERFACE.md`) - 데이터 교환 형식

---

## 📋 Data Interface

### AI1 → AI2: 콘텐츠 생성 요청

```json
{
  "keyword": "아이패드 프로",
  "trend_score": 95,
  "related_keywords": ["아이패드", "태블릿", "애플"],
  "product_info": {
    "products": [
      {
        "title": "상품명",
        "price": "가격",
        "image_url": "이미지URL",
        "product_url": "상품링크"
      }
    ],
    "total_count": 10
  },
  "collection_date": "2025-11-17"
}
```

### AI2 → AI1: 생성된 콘텐츠

```json
{
  "title": "부모들이 미친 듯 찾는 아이패드 프로, 왜 갑자기 인기일까?",
  "content_html": "<h2>섹션1</h2><p>내용...</p>",
  "images": ["image_url1", "image_url2"],
  "keywords": ["아이패드", "태블릿"],
  "created_at": "2025-11-17T10:00:00",
  "metadata": {
    "word_count": 1200,
    "seo_score": 85
  }
}
```

> 📄 상세 인터페이스 정의는 `INTERFACE.md` 참고

---

## 🛡️ Technical Considerations & Limitations

### 기술적 고려사항

1. **Selenium 자동화 안정성**
   - CAPTCHA, 2FA, IP 차단 등에 대한 대응 전략 필요
   - 재시도 로직 및 에러 핸들링 구현
   - GUI 모드 사용으로 안정성 향상

2. **API Rate Limiting**
   - OpenAI API 사용량 모니터링
   - 요청 간격 조절 및 배치 처리

3. **데이터 품질 관리**
   - 키워드 필터링 규칙 지속적 개선
   - 생성된 콘텐츠 품질 검증 로직

### 알려진 제한사항

- 네이버/티스토리 자동화는 플랫폼 정책 변경에 따라 동작하지 않을 수 있음
- Google Trends API는 비공식 API로 제한이 있을 수 있음
- 대량 요청 시 IP 차단 가능성

---

## 📊 Project Status

### ✅ 완료된 기능

- [x] 프로젝트 계획 수립
- [x] 상세 요구사항 정리 및 구조 설계
- [x] 환경 설정 및 기본 구조 생성
- [ ] ① 트렌드 데이터 수집 모듈 구현
- [ ] ③ ssadagu.kr 상품 수집 기능 구현
- [ ] ② AI 콘텐츠 생성 엔진 구현
- [ ] ④ 결과 저장 기능 구현
- [ ] ⑤ 스케줄러 구현

### 🚧 진행 중

- 환경 설정 및 협업 환경 구축

---

## 🌱 Future Improvements

- [ ] 서버 기반 Headless Selenium 전환 (Cloud Execution)
- [ ] Docker 기반 배포
- [ ] Google Shopping, YouTube Trends 확장
- [ ] 자동 광고 수익 분석 기능 추가
- [ ] 콘텐츠 품질 자동 검증 시스템
- [ ] 다중 LLM 모델 지원 (Claude, Gemini 등)

---

## 📝 License

본 프로젝트는 **교육 및 포트폴리오 목적**으로 개발되었으며,  
기술 검증 및 학습을 위한 PoC(Proof of Concept) 수준의 시스템입니다.

---

## ⚠️ Disclaimer

- 본 프로젝트는 **기술 검증 및 학습 목적**으로 개발되었습니다.
- 실제 블로그 서비스 자동화는 각 플랫폼의 이용약관을 확인해야 합니다.
- 상업적 운영이 아닌 **기술 구현 가능성 탐구** 수준의 프로젝트입니다.
- 실 운영 시 플랫폼 정책 및 법적 규정을 반드시 확인하세요.

---

## 👥 Contributors

- **AI 1**: Trend Data & Pipeline Engineer
- **AI 2**: AI Content Generation Engineer

---

## 📚 References

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [Pytrends Documentation](https://github.com/GeneralMills/pytrends)

---

**Made with ❤️ for AI Automation Learning**

