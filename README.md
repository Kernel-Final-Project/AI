# 📊 AI Trend-Based Blog Automation Project  

**Google Trends → ssadagu 상품 수집 → AI 콘텐츠 생성 → Naver Auto Posting**  

(로컬 환경 기반 자동 블로그 운영 시스템)

---

## 📌 Overview

이 프로젝트는 Google Trends 기반으로 **'오늘 뜨는 이슈 상품 50개'**를 자동 수집하고,  

그 중 **상품명 1개를 랜덤으로 선택한 뒤**,  

해당 키워드를 활용해 **ssadagu.kr 쇼핑몰에서 실제 상품 정보를 크롤링**하고,  

이를 바탕으로 **생성형 LLM(OpenAI GPT)**으로 블로그용 텍스트 콘텐츠를 생성한 후,  

**네이버 블로그에 자동 업로드**하는 **엔드-투-엔드 자동화 시스템**입니다.

> 매일 아침 08:00에 자동으로 실행되어  

> "트렌드 기반 + 실제 쇼핑몰 상품 정보 기반" 블로그 포스트를 자동으로 발행합니다.

---

## 🚀 Key Features

### 🔍 1. Google Trends 이슈 상품 50개 수집

- Google Trends에서 **이슈 상품/키워드 50개** 수집  

- 연관 검색어 및 주제 기반 확장  

- 점수 기반 상위 키워드 정렬  

---

### 🎯 2. 트렌드 상품 1개 랜덤 선택

- 수집된 50개 키워드 중 1개 자동 랜덤 선택  

- 매일 새로운 주제로 글 생성  

---

### 🛒 3. ssadagu.kr 쇼핑몰 상품 수집 (필수 기능)

- 선택된 키워드를 기반으로 ssadagu.kr 검색  

- 상품 제목 목록 크롤링  

- LLM 입력용 상품 텍스트 데이터 생성  

> 단순 키워드 AI 글이 아닌  

> **"실제 쇼핑몰 상품 데이터를 활용한 고품질 콘텐츠"**를 생성하기 위한 핵심 기능.

---

### ✍️ 4. AI 텍스트 콘텐츠 생성 (OpenAI GPT)

- SEO 기반 제목 생성  

- h2/h3 기반 구조화 아웃라인 생성  

- 자연스럽고 읽기 쉬운 1,000~1,500자 본문 생성  

- 광고 느낌 최소화  

- DALL·E 기반 이미지 자동 생성(옵션)  

- 최종 HTML 템플릿으로 자동 변환  

---

### 🚀 5. 네이버 블로그 자동 업로드 (Selenium)

- 네이버 계정 자동 로그인  

- 블로그 글쓰기 페이지 진입  

- 생성된 HTML 본문 자동 입력  

- 이미지 업로드(옵션)  

- 제목/내용 자동 입력  

- 자동 발행  

> GUI 모드 Selenium 기반  

> 로컬 환경에서 안정적으로 동작하도록 구성됨.

---

### ⏱ 6. 매일 08:00 자동 실행

- Python schedule  

- 전체 파이프라인 자동 실행  

  - Google Trends 수집  

  - 키워드 랜덤 선택  

  - ssadagu.kr 상품 데이터 수집  

  - AI 콘텐츠 생성  

  - 네이버 자동 업로드  

---

### 🌟 Optional Feature: 티스토리 자동 업로드

- 네이버 외 티스토리 블로그 자동 발행 기능 확장 가능  

- 옵션 기능으로 모듈 구조만 제공  

---

## 🧩 System Architecture

```
┌───────────────┐
│ Google Trends │
└───────┬───────┘
        ▼
┌─────────────────────────────┐
│ Trend Collector             │
│ - 이슈 상품 50개 수집        │
└───────┬─────────────────────┘
        ▼
┌─────────────────────────────┐
│ Keyword Selector            │
│ - 상품명 1개 랜덤 선택       │
└───────┬─────────────────────┘
        ▼
┌─────────────────────────────┐
│ ssadagu Scraper             │
│ - 상품 제목 크롤링           │
└───────┬─────────────────────┘
        ▼
┌─────────────────────────────┐
│ AI Content Engine (GPT)     │
│ - 제목/아웃라인/본문 생성    │
└───────┬─────────────────────┘
        ▼
┌─────────────────────────────┐
│ Naver Blog Uploader         │
│ - Selenium 자동 업로드       │
└───────┬─────────────────────┘
        ▼
┌──────────────────────────────┐
│ Local Scheduler (08:00 Daily)│
└──────────────────────────────┘
```

---

## 🗂 Folder Structure

```
ai-blog-project/
│
├── trends/
│   ├── trends_collector.py       # Google Trends 50개 수집
│   ├── keyword_selector.py       # 랜덤 키워드 선택
│
├── ssadagu/
│   ├── ssadagu_scraper.py        # ssadagu.kr 상품 제목 수집
│
├── content_ai/
│   ├── prompt_builder.py
│   ├── content_generator.py
│   ├── html_formatter.py
│
├── auto_posting/
│   ├── naver_uploader.py
│   ├── tistory_uploader.py       # (옵션)
│   ├── browser_utils.py
│
├── scheduler/
│   ├── main_scheduler.py          # 매일 08:00 전체 실행
│
├── utils/
│   ├── load_env.py
│   ├── logger.py
│   ├── file_manager.py
│
├── data/
│   ├── keywords/
│   ├── ssadagu/
│   ├── posts/
│
├── .env
├── requirements.txt
└── README.md
```

---

## 🧪 Installation

### 1. Clone repository  

```bash
git clone https://github.com/Kernel-Final-Project/AI.git
cd AI
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

### 4. Set environment variables (.env)  

`.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

```env
OPENAI_API_KEY=your_openai_api_key
NAVER_ID=your_naver_id
NAVER_PW=your_naver_pw
TISTORY_ID=your_tistory_id      # (옵션)
TISTORY_PW=your_tistory_pw      # (옵션)
```

---

## ▶️ Usage

### 1) 전체 자동 파이프라인 실행  

```bash
python scheduler/main_scheduler.py
```

### 2) 개별 모듈 실행  

트렌드 수집:

```bash
python trends/trends_collector.py
```

키워드 선택:

```bash
python trends/keyword_selector.py
```

ssadagu 상품 수집:

```bash
python ssadagu/ssadagu_scraper.py
```

AI 콘텐츠 생성:

```bash
python content_ai/content_generator.py
```

네이버 업로드:

```bash
python auto_posting/naver_uploader.py
```

---

## 🧑‍🤝‍🧑 Roles

### 👤 AI 1 — Trend & Data Engineer

- Google Trends 키워드 50개 수집  

- 랜덤 제품 선택  

- ssadagu 상품 정보 크롤링  

- 데이터 구조 설계/저장  

- 스케줄러 통합

### 👤 AI 2 — AI Content & Automation Engineer

- GPT 프롬프트 설계  

- 콘텐츠 생성 엔진 구축  

- HTML 템플릿 제작  

- 네이버/티스토리 자동 업로드 개발  

---

## 🌱 Future Improvements

- Headless Chrome 기반 서버 배포  

- Docker 기반 확장  

- 다른 쇼핑몰(쿠팡/11번가/G마켓) 확장  

- 가격/리뷰/스펙 기반 비교 리뷰 생성  

- 자동 수익 분석 리포트 기능 추가  

---

## 📝 License

본 프로젝트는 교육 및 포트폴리오 목적의 코드이며  

무단 상업적 이용을 금지합니다.

