# 환경 설정 가이드

## 현재 상태
- Python 가상환경(venv)이 이미 생성되어 있습니다.
- Python 버전: 3.9

## 환경 설정 단계

### 1단계: 가상환경 활성화
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2단계: 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

### 3단계: 환경변수 설정
`.env` 파일을 생성하고 필요한 정보를 입력합니다.

### 4단계: 프로젝트 구조 생성
디렉토리 구조를 생성합니다.

## 다음 단계
환경 설정이 완료되면 각 기능 모듈을 순차적으로 구현합니다.

