# 📊 AI Trend-Based Blog Automation Project  
**Google Trends → AI Content Generation → Naver/Tistory Auto Posting**  
(로컬 환경 기반 자동 블로그 운영 시스템)

---

## 📌 Overview

이 프로젝트는 Google Trends 기반으로 **'오늘 뜨는 이슈 상품 50개'**를 자동 수집하고,  
OpenAI GPT를 활용해 블로그용 고품질 콘텐츠를 자동 생성한 뒤,  
**Selenium을 이용해 네이버 블로그와 티스토리에 자동 업로드**하는  
**완전 자동화 콘텐츠 운영 시스템(AI Blogging Automation System)**입니다.

본 프로젝트는 실제 개인/기업 블로그 자동 운영 시스템과 유사한 흐름을 가지며,  
크롤링·AI·자동화 기술을 모두 활용하는 실전형 포트폴리오 프로젝트입니다.

---

## 🚀 Key Features

### 🔍 1. Google Trends 기반 트렌드 키워드 자동 수집
- 최신 트렌드 상품 키워드 50개 자동 수집  
- Pytrends + Selenium 기반 복합 크롤링  
- 관련 검색어·관련 주제 확장  
- 불필요 키워드 필터링(연예/정치/뉴스 등)  
- 점수 기반 상위 30~50개 선별  

---

### ✍️ 2. AI 콘텐츠 자동 생성 (OpenAI GPT)
- SEO 기반 제목 자동 생성  
- h2/h3 포함 아웃라인 자동 생성  
- 1,000~1,500자 본문 자동 생성  
- 광고 느낌 없는 자연스러운 문체  
- DALL·E 기반 이미지 자동 생성(옵션)  
- 최종 HTML 템플릿 자동 구성  

---

### 🚀 3. 블로그 자동 업로드 (Selenium)
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

> ⚠️ 본 프로젝트는 **로컬 환경에서 GUI 모드로 Selenium 브라우저를 직접 띄우는 방식**으로 안정적으로 작동하도록 개발되었습니다.

---

### ⏱ 4. 로컬 스케줄링 기반 자동화
- Python schedule 사용  
- 매일 오전 10시 자동 실행  
  → 트렌드 수집 → 콘텐츠 생성 → 블로그 업로드  
- 로깅 시스템으로 작업 기록 저장  

---

## 🧩 System Architecture

```
┌───────────────┐
│ Google Trends │
└───────┬───────┘
        ▼
┌────────────────────────┐
│ Trend Crawler (AI1)    │
│ - Pytrends/Selenium    │
│ - Keyword Expansion    │
└───────┬────────────────┘
        ▼
┌────────────────────────┐
│ AI Content Engine (AI2)│
│ - Title Generator      │
│ - Outline Generator    │
│ - Post Generator (GPT) │
│ - DALL·E Image Maker   │
└───────┬────────────────┘
        ▼
┌────────────────────────┐
│ Auto Posting System    │
│ - Naver Uploader       │
│ - Tistory Uploader     │
│ (Selenium GUI)         │
└───────┬────────────────┘
        ▼
┌────────────────────────┐
│ Local Scheduler         │
│ (Python schedule)       │
└────────────────────────┘
```

---

## 🗂 Folder Structure

```
ai-blog-project/
│
├── ai1_trends/                 
│   ├── trends_crawler.py       
│   ├── keyword_expand.py       
│   ├── keyword_filter.py       
│   ├── scheduler_trends.py     
│
├── ai2_content/                
│   ├── title_generator.py      
│   ├── outline_generator.py    
│   ├── content_generator.py    
│   ├── image_generator.py      
│   ├── html_formatter.py       
│   ├── scheduler_content.py    
│
├── auto_posting/               
│   ├── naver_uploader.py       
│   ├── tistory_uploader.py     
│   ├── browser_utils.py        
│
├── utils/
│   ├── load_env.py
│   ├── logger.py
│   ├── file_manager.py
│
├── data/
│   ├── keywords/
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
git clone https://github.com/YOUR-NAME/ai-blog-project.git
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

### 4. Environment variables (.env)
```
OPENAI_API_KEY=your_api_key_here

NAVER_ID=your_id
NAVER_PW=your_pw

TISTORY_ID=your_id
TISTORY_PW=your_pw
```

---

## ▶️ Usage

### 🔍 1. 트렌드 수집
```bash
python ai1_trends/scheduler_trends.py
```

### ✍️ 2. 콘텐츠 생성
```bash
python ai2_content/scheduler_content.py
```

### 🚀 3. 블로그 자동 업로드  
**네이버**
```bash
python auto_posting/naver_uploader.py
```

**티스토리**
```bash
python auto_posting/tistory_uploader.py
```

---

## 🧑‍🤝‍🧑 Roles

### 👤 AI 1 — Trend Data Engineer
- Google Trends 크롤링  
- 키워드 확장/필터링  
- 스케줄링 기반 자동 키워드 생성  

### 👤 AI 2 — AI Content & Automation Engineer
- GPT 프롬프트 설계  
- 콘텐츠 생성 엔진 개발  
- HTML 템플릿 구성  
- 네이버/티스토리 자동 업로드 기능 개발  

---

## 🌱 Future Improvements
- 서버 기반 Headless Selenium 전환(Cloud Execution)  
- Docker 기반 배포  
- 음성 기반 블로그 자동화  
- Google Shopping, YouTube Trends 확장  
- 자동 광고 수익 분석 기능 추가  

---

## 📝 License
본 프로젝트는 교육/포트폴리오 목적이며 상업적 이용은 금지됩니다.
