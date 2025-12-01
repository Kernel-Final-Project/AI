# 디렉토리 재구성 완료

## 변경 사항 요약

### 1. 크롤러 모듈 통합 ✅
- **이전**: `ssadagu/`, `ssadagu_parser/`, `musinsa_parser/`, `scraper/` (분산)
- **이후**: `parsers/` (통합)
  - `parsers/ssadagu/` - 싸다구 크롤러
  - `parsers/musinsa/` - 무신사 크롤러
  - `parsers/base/` - 공통 스크래퍼 유틸리티

### 2. 테스트 파일 정리 ✅
- **이전**: 루트에 `test_*.py` 30개 이상 산재
- **이후**: `tests/` 하위로 분류
  - `tests/parsers/` - 크롤러 테스트
  - `tests/content/` - 콘텐츠 생성 테스트
  - `tests/posting/` - 업로드 테스트
  - `tests/utils/` - 유틸리티 테스트

### 3. 디버깅/스크립트 정리 ✅
- **이전**: 루트에 `debug_*.py`, `check_*.py` 산재
- **이후**: `scripts/` 하위로 분류
  - `scripts/debug/` - 디버깅 스크립트
  - `scripts/utils/` - 유틸리티 스크립트
  - `scripts/check/` - 체크 스크립트

### 4. 문서 정리 ✅
- **이전**: 루트에 `.md` 파일 10개 이상 산재
- **이후**: `docs/` 하위로 분류
  - `docs/setup/` - 설정 관련 문서
  - `docs/development/` - 개발 관련 문서
  - `docs/analysis/` - 분석 문서

## 새로운 디렉토리 구조

```
final_project_AI/
├── parsers/                 # 크롤러 모듈 (통합)
│   ├── ssadagu/            # 싸다구 크롤러
│   ├── musinsa/            # 무신사 크롤러
│   └── base/               # 공통 스크래퍼 유틸리티
├── trends/                 # 트렌드 수집
├── content_ai/             # AI 콘텐츠 생성
├── auto_posting/           # 블로그 자동 업로드
├── scheduler/              # 스케줄링
├── utils/                  # 공통 유틸리티
├── storage/                # 데이터 저장
├── tests/                  # 모든 테스트 파일
│   ├── parsers/
│   ├── content/
│   ├── posting/
│   └── utils/
├── scripts/                # 디버깅/유틸리티 스크립트
│   ├── debug/
│   ├── utils/
│   └── check/
├── docs/                   # 문서 파일
│   ├── setup/
│   ├── development/
│   └── analysis/
├── data/                   # 데이터 (gitignore)
├── logs/                   # 로그 (gitignore)
└── README.md               # 메인 README
```

## Import 경로 변경

### 변경 전
```python
from musinsa_parser.crawler import crawl_from_main
from ssadagu_parser.config import BASE_URL
from scraper.html_extractor import extract_html
```

### 변경 후
```python
from parsers.musinsa.crawler import crawl_from_main
from parsers.ssadagu.config import BASE_URL
from parsers.base.html_extractor import extract_html
```

## 기존 디렉토리 처리

다음 디렉토리들은 아직 남아있습니다 (백업용):
- `ssadagu/` - 구버전? (확인 필요)
- `ssadagu_parser/` - 이미 `parsers/ssadagu/`로 복사됨
- `musinsa_parser/` - 이미 `parsers/musinsa/`로 복사됨
- `scraper/` - 이미 `parsers/base/`로 복사됨

**권장 사항**: 
1. 새 구조로 테스트 완료 후
2. 기존 디렉토리 삭제 또는 `archive/` 폴더로 이동

## 주의 사항

1. **루트에 남은 파일들**:
   - `README.md`, `README_FINAL.md` - 통합 필요
   - `ssadagu/` - 확인 필요 (구버전인지)

2. **Import 경로**:
   - 모든 파일의 import 경로가 수정되었지만
   - 일부 파일에서 누락될 수 있으니 테스트 필요

3. **기존 디렉토리**:
   - `ssadagu_parser/`, `musinsa_parser/`, `scraper/`는 백업용으로 남겨둠
   - 테스트 완료 후 삭제 권장

