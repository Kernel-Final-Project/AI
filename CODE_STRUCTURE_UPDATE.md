# 코드 구조 업데이트 문서

## 📅 업데이트 날짜
2025-11-19

## 🎯 업데이트 목적
GPT 관련 공통 함수들을 `gpt_utils.py`로 분리하여 재사용성과 유지보수성을 향상

---

## 📁 변경된 파일 구조

### 1. 새로 생성된 파일

#### `content_ai/gpt_utils.py`
- **역할**: GPT 관련 공통 유틸리티 함수 모음
- **담당**: AI2

**주요 함수:**
- `get_client()`: OpenAI 클라이언트 인스턴스 가져오기 (싱글톤 패턴)
- `generate_with_prompt()`: 프롬프트 파일을 사용하여 텍스트 생성 (공통 함수)
- `parse_json_response()`: JSON 형식의 응답을 파싱

---

### 2. 수정된 파일

#### `content_ai/content_generator.py`
- **변경 사항**: 공통 로직을 `gpt_utils.py`로 이동

**변경 전:**
- 클라이언트 인스턴스를 직접 생성
- `test_openai_connection()` 함수만 존재

**변경 후:**
- `gpt_utils.py`의 공통 함수들을 import하여 사용
- `test_openai_connection()` 함수 개선

---

## 🔄 주요 변경 사항

### 1. 클라이언트 관리 방식 변경

**이전:**
```python
# content_generator.py에서 직접 생성
client = OpenAIClient()
```

**현재:**
```python
# gpt_utils.py에서 싱글톤 패턴으로 관리
_client = None

def get_client():
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
```

**장점:**
- 클라이언트 인스턴스를 한 번만 생성 (메모리 효율)
- 여러 모듈에서 동일한 인스턴스 사용 가능

---

### 2. 공통 함수 추가

#### `generate_with_prompt()`
- 프롬프트 파일 로드 + API 호출을 하나의 함수로 통합
- 모든 생성 함수에서 재사용 가능

**사용 예시:**
```python
result = generate_with_prompt(
    prompt_name="title_prompt",
    user_data={
        "키워드": "요가매트",
        "상품 정보": "프리미엄 요가매트"
    }
)
```

---

## 📊 파일 간 의존성

```
gpt_utils.py
    ↓ (import)
    ├── openai_client.py
    ├── prompt_builder.py
    └── utils/load_env.py

content_generator.py
    ↓ (import)
    └── gpt_utils.py
```

---

## 🎨 설계 원칙

### 1. 관심사의 분리 (Separation of Concerns)
- **gpt_utils.py**: 공통 유틸리티 로직
- **content_generator.py**: 테스트 및 유틸리티 함수
- **openai_client.py**: OpenAI API 래퍼

### 2. DRY (Don't Repeat Yourself)
- 공통 로직을 `generate_with_prompt()`로 통합
- 중복 코드 제거

### 3. 싱글톤 패턴
- 클라이언트 인스턴스를 한 번만 생성
- 메모리 효율성 향상

---

## ✅ 장점

1. **재사용성**: `generate_with_prompt()`를 여러 곳에서 사용 가능
2. **유지보수성**: 공통 로직을 한 곳에서 관리
3. **확장성**: 새로운 함수 추가가 쉬움
4. **테스트 용이성**: 공통 함수를 독립적으로 테스트 가능
5. **코드 가독성**: 각 파일의 역할이 명확함

---

## 🔧 사용 방법

### 공통 함수 직접 사용
```python
from content_ai.gpt_utils import generate_with_prompt

result = generate_with_prompt(
    prompt_name="custom_prompt",
    user_data={"key": "value"},
    model="gpt-4o-mini",
    temperature=0.7
)
```

---

## 📝 향후 개선 사항

1. 에러 핸들링 강화
2. 재시도 로직 추가
3. 응답 캐싱 기능
4. 프롬프트 버전 관리

---

## 🔗 관련 파일

- `content_ai/gpt_utils.py`: 공통 유틸리티 함수
- `content_ai/content_generator.py`: 테스트 함수
- `content_ai/openai_client.py`: OpenAI API 클라이언트
- `content_ai/prompt_builder.py`: 프롬프트 빌더

