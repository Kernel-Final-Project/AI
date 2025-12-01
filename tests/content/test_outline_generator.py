"""
아웃라인 생성 모듈 테스트
"""
import json
from content_ai.outline_generator import (
    generate_outline,
    generate_outlines,
    parse_outline_from_response,
    parse_markdown_outline,
    validate_outline,
    create_fallback_outline
)
from utils.logger import logger


def test_outline_generation():
    """아웃라인 생성 통합 테스트 (실제 GPT 호출)"""
    print("=" * 60)
    print("아웃라인 생성 모듈 테스트")
    print("=" * 60)
    
    # 테스트 데이터
    keyword = "요가매트"
    title = "요가매트 추천 가이드 2025년 완벽 정리"
    product_info = "싸다구 프리미엄 요가매트, 두께 10mm, 미끄럼 방지"
    
    print(f"\n[테스트 데이터]")
    print(f"키워드: {keyword}")
    print(f"제목: {title}")
    print(f"상품 정보: {product_info}")
    
    # 통합 함수 테스트
    print(f"\n[1] 통합 함수 테스트 (generate_outline)")
    print("GPT 호출 중... (시간이 걸릴 수 있습니다)")
    
    outline = generate_outline(keyword, title, product_info)
    
    if outline and "h2" in outline:
        h2_count = len(outline["h2"])
        print(f"✅ 아웃라인 생성 성공: h2 {h2_count}개")
        
        print("\n생성된 아웃라인:")
        for i, h2_item in enumerate(outline["h2"], 1):
            print(f"\n  h2[{i}]: {h2_item['title']} ({len(h2_item['title'])}자)")
            for j, h3_title in enumerate(h2_item.get("h3", []), 1):
                print(f"    h3[{j}]: {h3_title} ({len(h3_title)}자)")
        
        # 검증 테스트
        print(f"\n[2] 검증 테스트")
        is_valid = validate_outline(outline, keyword)
        if is_valid:
            print("✅ 아웃라인 검증 통과")
        else:
            print("❌ 아웃라인 검증 실패")
            return False
        
        # JSON 출력
        print(f"\n[3] JSON 형식 확인")
        outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
        print("✅ JSON 형식 정상")
        print(f"\n생성된 JSON (일부):")
        print(outline_json[:200] + "..." if len(outline_json) > 200 else outline_json)
        
    else:
        print("❌ 아웃라인 생성 실패")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 통합 테스트 통과!")
    print("=" * 60)
    return True


def test_parse_outline():
    """파싱 함수 테스트 (하드코딩된 응답)"""
    print("\n" + "=" * 60)
    print("[테스트 2] 파싱 함수 테스트")
    print("=" * 60)
    
    # 케이스 1: 정상 JSON 응답
    print("\n[케이스 1] 정상 JSON 응답")
    response1 = json.dumps({
        "h2": [
            {
                "title": "요가매트 개요",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징",
                "h3": ["요가매트 주요 특징", "요가매트 장점"]
            },
            {
                "title": "요가매트 활용",
                "h3": ["요가매트 사용 방법"]
            }
        ]
    })
    outline1 = parse_outline_from_response(response1)
    print(f"결과: h2 {len(outline1.get('h2', []))}개 파싱")
    assert "h2" in outline1, "h2 키가 있어야 함"
    assert len(outline1["h2"]) == 3, "h2가 3개여야 함"
    print("✅ 정상 JSON 파싱 성공")
    
    # 케이스 2: 코드 블록 포함된 응답
    print("\n[케이스 2] 코드 블록 포함된 응답")
    response2 = """```json
{
  "h2": [
    {
      "title": "요가매트 개요",
      "h3": ["요가매트 기본 정보"]
    },
    {
      "title": "요가매트 특징",
      "h3": ["요가매트 주요 특징"]
    }
  ]
}
```"""
    outline2 = parse_outline_from_response(response2)
    print(f"결과: h2 {len(outline2.get('h2', []))}개 파싱")
    assert "h2" in outline2, "h2 키가 있어야 함"
    assert len(outline2["h2"]) == 2, "h2가 2개여야 함"
    print("✅ 코드 블록 제거 후 파싱 성공")
    
    # 케이스 3: Markdown 형식 응답
    print("\n[케이스 3] Markdown 형식 응답")
    response3 = """## 요가매트 개요
### 요가매트 기본 정보

## 요가매트 특징
### 요가매트 주요 특징
### 요가매트 장점

## 요가매트 활용
### 요가매트 사용 방법"""
    outline3 = parse_outline_from_response(response3)
    print(f"결과: h2 {len(outline3.get('h2', []))}개 파싱")
    assert "h2" in outline3, "h2 키가 있어야 함"
    assert len(outline3["h2"]) == 3, "h2가 3개여야 함"
    assert outline3["h2"][0]["title"] == "요가매트 개요", "첫 번째 h2 제목이 올바르게 파싱되어야 함"
    assert len(outline3["h2"][1]["h3"]) == 2, "두 번째 h2의 h3가 2개여야 함"
    print("✅ Markdown 형식 파싱 성공")
    
    # 케이스 4: 잘못된 형식
    print("\n[케이스 4] 잘못된 형식")
    response4 = "이것은 JSON도 Markdown도 아닙니다"
    outline4 = parse_outline_from_response(response4)
    print(f"결과: {outline4}")
    assert outline4 == {} or "raw" in outline4, "빈 딕셔너리 또는 raw 키가 있어야 함"
    print("✅ 잘못된 형식 처리 성공")
    
    print("\n✅ 파싱 테스트 완료")


def test_parse_markdown_outline():
    """Markdown 파서 전용 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 2-1] Markdown 파서 전용 테스트")
    print("=" * 60)
    
    # 케이스 1: 기본 Markdown 형식 (h2 + h3)
    print("\n[케이스 1] 기본 Markdown 형식")
    md1 = """## 요가매트 개요
### 요가매트 기본 정보

## 요가매트 특징
### 요가매트 주요 특징
### 요가매트 장점"""
    result1 = parse_markdown_outline(md1)
    assert "h2" in result1, "h2 키가 있어야 함"
    assert len(result1["h2"]) == 2, "h2가 2개여야 함"
    assert result1["h2"][0]["title"] == "요가매트 개요", "첫 번째 h2 제목 확인"
    assert len(result1["h2"][0]["h3"]) == 1, "첫 번째 h2의 h3가 1개여야 함"
    assert len(result1["h2"][1]["h3"]) == 2, "두 번째 h2의 h3가 2개여야 함"
    print("✅ 기본 Markdown 형식 파싱 성공")
    
    # 케이스 2: h2만 있고 h3 없는 경우
    print("\n[케이스 2] h2만 있고 h3 없는 경우")
    md2 = """## 요가매트 개요

## 요가매트 특징

## 요가매트 활용"""
    result2 = parse_markdown_outline(md2)
    assert len(result2["h2"]) == 3, "h2가 3개여야 함"
    assert len(result2["h2"][0]["h3"]) == 0, "h3가 없어야 함"
    print("✅ h2만 있는 경우 파싱 성공")
    
    # 케이스 3: h2 없이 h3만 있는 경우 (빈 h2 생성 확인)
    print("\n[케이스 3] h2 없이 h3만 있는 경우")
    md3 = """### 요가매트 기본 정보
### 요가매트 특징"""
    result3 = parse_markdown_outline(md3)
    assert len(result3["h2"]) == 1, "빈 h2가 1개 생성되어야 함"
    assert result3["h2"][0]["title"] == "", "h2 제목이 빈 문자열이어야 함"
    assert len(result3["h2"][0]["h3"]) == 2, "h3가 2개여야 함"
    print("✅ h2 없이 h3만 있는 경우 처리 성공")
    
    # 케이스 4: 공백과 특수문자 포함된 제목
    print("\n[케이스 4] 공백과 특수문자 포함된 제목")
    md4 = """##  요가매트 개요  정보  
###  요가매트 기본 정보  

## 요가매트 특징 분석
### 요가매트 주요 특징"""
    result4 = parse_markdown_outline(md4)
    assert result4["h2"][0]["title"] == "요가매트 개요  정보", "공백이 제거되어야 함"
    assert result4["h2"][0]["h3"][0] == "요가매트 기본 정보", "h3 공백 제거 확인"
    print("✅ 공백 처리 성공")
    
    # 케이스 5: 빈 줄이 많은 경우
    print("\n[케이스 5] 빈 줄이 많은 경우")
    md5 = """## 요가매트 개요


### 요가매트 기본 정보



## 요가매트 특징


### 요가매트 주요 특징"""
    result5 = parse_markdown_outline(md5)
    assert len(result5["h2"]) == 2, "h2가 2개여야 함"
    assert len(result5["h2"][0]["h3"]) == 1, "h3가 1개여야 함"
    print("✅ 빈 줄 처리 성공")
    
    # 케이스 6: 제목 앞뒤에 #가 추가로 있는 경우
    print("\n[케이스 6] 제목 앞뒤에 #가 추가로 있는 경우")
    md6 = """## #요가매트 개요#
### #요가매트 기본 정보#

## 요가매트 특징
### 요가매트 주요 특징"""
    result6 = parse_markdown_outline(md6)
    assert result6["h2"][0]["title"] == "요가매트 개요", "추가 # 제거 확인"
    assert result6["h2"][0]["h3"][0] == "요가매트 기본 정보", "h3 추가 # 제거 확인"
    print("✅ 추가 # 제거 성공")
    
    print("\n✅ Markdown 파서 테스트 완료")


def test_parse_outline_integration():
    """통합 파서 테스트 (JSON + Markdown 혼합, 실제 GPT 응답 시뮬레이션)"""
    print("\n" + "=" * 60)
    print("[테스트 2-2] 통합 파서 테스트")
    print("=" * 60)
    
    # 케이스 1: 설명 텍스트 + JSON 혼합
    print("\n[케이스 1] 설명 텍스트 + JSON 혼합")
    response1 = """다음은 아웃라인입니다:

{
  "h2": [
    {
      "title": "요가매트 개요",
      "h3": ["요가매트 기본 정보"]
    },
    {
      "title": "요가매트 특징",
      "h3": ["요가매트 주요 특징"]
    }
  ]
}"""
    result1 = parse_outline_from_response(response1)
    assert "h2" in result1, "h2 키가 있어야 함"
    assert len(result1["h2"]) == 2, "h2가 2개여야 함"
    print("✅ 설명 + JSON 혼합 파싱 성공")
    
    # 케이스 2: 설명 텍스트 + Markdown 혼합
    print("\n[케이스 2] 설명 텍스트 + Markdown 혼합")
    response2 = """아래는 생성된 아웃라인입니다:

## 요가매트 개요
### 요가매트 기본 정보

## 요가매트 특징
### 요가매트 주요 특징
### 요가매트 장점

이 아웃라인을 참고하세요."""
    result2 = parse_outline_from_response(response2)
    assert "h2" in result2, "h2 키가 있어야 함"
    assert len(result2["h2"]) == 2, "h2가 2개여야 함"
    assert len(result2["h2"][1]["h3"]) == 2, "두 번째 h2의 h3가 2개여야 함"
    print("✅ 설명 + Markdown 혼합 파싱 성공")
    
    # 케이스 3: JSON 코드 블록 + Markdown 혼합
    print("\n[케이스 3] JSON 코드 블록 + Markdown 혼합")
    response3 = """```json
{
  "h2": [
    {
      "title": "요가매트 개요",
      "h3": ["요가매트 기본 정보"]
    }
  ]
}
```

또는 Markdown 형식으로:

## 요가매트 특징
### 요가매트 주요 특징"""
    result3 = parse_outline_from_response(response3)
    # JSON이 우선이므로 JSON 결과가 나와야 함
    assert "h2" in result3, "h2 키가 있어야 함"
    print("✅ 코드 블록 + Markdown 혼합 처리 성공")
    
    # 케이스 4: Markdown 코드 블록 포함
    print("\n[케이스 4] Markdown 코드 블록 포함")
    response4 = """```markdown
## 요가매트 개요
### 요가매트 기본 정보

## 요가매트 특징
### 요가매트 주요 특징
```"""
    result4 = parse_outline_from_response(response4)
    assert "h2" in result4, "h2 키가 있어야 함"
    assert len(result4["h2"]) == 2, "h2가 2개여야 함"
    print("✅ Markdown 코드 블록 파싱 성공")
    
    # 케이스 5: JSON 파싱 실패 후 Markdown으로 자동 전환
    print("\n[케이스 5] JSON 파싱 실패 후 Markdown 자동 전환")
    response5 = """{잘못된 JSON 형식}

## 요가매트 개요
### 요가매트 기본 정보

## 요가매트 특징
### 요가매트 주요 특징"""
    result5 = parse_outline_from_response(response5)
    assert "h2" in result5, "Markdown으로 자동 전환되어야 함"
    assert len(result5["h2"]) == 2, "h2가 2개여야 함"
    print("✅ JSON 실패 후 Markdown 자동 전환 성공")
    
    # 케이스 6: 복잡한 설명 + JSON 혼합
    print("\n[케이스 6] 복잡한 설명 + JSON 혼합")
    response6 = """아웃라인을 생성했습니다.
다음 JSON 형식으로 제공됩니다:

{
  "h2": [
    {
      "title": "요가매트 개요",
      "h3": ["요가매트 기본 정보", "요가매트 종류"]
    },
    {
      "title": "요가매트 특징",
      "h3": ["요가매트 주요 특징"]
    },
    {
      "title": "요가매트 활용",
      "h3": ["요가매트 사용 방법"]
    }
  ]
}

이 아웃라인을 사용하세요."""
    result6 = parse_outline_from_response(response6)
    assert len(result6["h2"]) == 3, "h2가 3개여야 함"
    assert len(result6["h2"][0]["h3"]) == 2, "첫 번째 h2의 h3가 2개여야 함"
    print("✅ 복잡한 설명 + JSON 혼합 파싱 성공")
    
    # 케이스 7: 여러 줄 설명 + Markdown 혼합
    print("\n[케이스 7] 여러 줄 설명 + Markdown 혼합")
    response7 = """아래 아웃라인을 참고하세요.


## 요가매트 개요
### 요가매트 기본 정보
### 요가매트 종류

## 요가매트 특징
### 요가매트 주요 특징

위 아웃라인을 사용하면 됩니다."""
    result7 = parse_outline_from_response(response7)
    assert len(result7["h2"]) == 2, "h2가 2개여야 함"
    assert len(result7["h2"][0]["h3"]) == 2, "첫 번째 h2의 h3가 2개여야 함"
    print("✅ 여러 줄 설명 + Markdown 혼합 파싱 성공")
    
    print("\n✅ 통합 파서 테스트 완료")


def test_validate_outline():
    """검증 함수 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 3] 검증 함수 테스트")
    print("=" * 60)
    
    keyword = "요가매트"
    
    # 케이스 1: 정상 아웃라인
    print("\n[케이스 1] 정상 아웃라인")
    outline1 = {
        "h2": [
            {
                "title": "요가매트 개요 정보",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징", "요가매트 장점 분석"]
            },
            {
                "title": "요가매트 활용 방법",
                "h3": ["요가매트 사용 방법"]
            },
            {
                "title": "요가매트 비교 분석",
                "h3": ["요가매트 선택 가이드"]
            }
        ]
    }
    is_valid1 = validate_outline(outline1, keyword)
    print(f"결과: {'✅ 검증 통과' if is_valid1 else '❌ 검증 실패'}")
    assert is_valid1, "정상 아웃라인은 검증 통과해야 함"
    
    # 케이스 2: h2 개수 부족 (2개만)
    print("\n[케이스 2] h2 개수 부족 (2개만)")
    outline2 = {
        "h2": [
            {
                "title": "요가매트 개요",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징",
                "h3": ["요가매트 주요 특징"]
            }
        ]
    }
    is_valid2 = validate_outline(outline2, keyword)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid2 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid2, "h2가 2개만 있으면 검증 실패해야 함"
    
    # 케이스 3: h2 제목이 15자 이상
    print("\n[케이스 3] h2 제목이 15자 이상")
    outline3 = {
        "h2": [
            {
                "title": "요가매트 개요 및 기본 정보",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징"]
            },
            {
                "title": "요가매트 활용 방법",
                "h3": ["요가매트 사용 방법"]
            }
        ]
    }
    is_valid3 = validate_outline(outline3, keyword)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid3 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid3, "h2 제목이 15자 이상이면 검증 실패해야 함"
    
    # 케이스 3-2: h2 제목이 7자 미만
    print("\n[케이스 3-2] h2 제목이 7자 미만")
    outline3_2 = {
        "h2": [
            {
                "title": "요가매트",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징"]
            },
            {
                "title": "요가매트 활용 방법",
                "h3": ["요가매트 사용 방법"]
            }
        ]
    }
    is_valid3_2 = validate_outline(outline3_2, keyword)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid3_2 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid3_2, "h2 제목이 7자 미만이면 검증 실패해야 함"
    
    # 케이스 4: h3 개수 초과 (3개)
    print("\n[케이스 4] h3 개수 초과 (3개)")
    outline4 = {
        "h2": [
            {
                "title": "요가매트 개요",
                "h3": ["요가매트 기본 정보", "요가매트 특징", "요가매트 활용"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징"]
            },
            {
                "title": "요가매트 활용 방법",
                "h3": ["요가매트 사용 방법"]
            }
        ]
    }
    is_valid4 = validate_outline(outline4, keyword)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid4 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid4, "h3가 3개 이상이면 검증 실패해야 함"
    
    # 케이스 5: 키워드 포함 부족 (2개만)
    print("\n[케이스 5] 키워드 포함 부족 (2개만)")
    outline5 = {
        "h2": [
            {
                "title": "요가매트 개요 정보",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징"]
            },
            {
                "title": "활용 방법 정리",
                "h3": ["사용 방법 안내"]
            }
        ]
    }
    is_valid5 = validate_outline(outline5, keyword)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid5 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid5, "키워드가 포함된 h2가 2개만 있으면 검증 실패해야 함"
    
    print("\n✅ 검증 테스트 완료")


def test_fallback_outline():
    """폴백 아웃라인 생성 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 4] 폴백 아웃라인 생성 테스트")
    print("=" * 60)
    
    keyword = "요가매트"
    title = "요가매트 추천 가이드"
    product_info = "프리미엄 요가매트"
    
    fallback = create_fallback_outline(keyword, title, product_info)
    
    print(f"\n생성된 폴백 아웃라인:")
    print(f"h2 개수: {len(fallback.get('h2', []))}개")
    
    for i, h2_item in enumerate(fallback["h2"], 1):
        print(f"\n  h2[{i}]: {h2_item['title']}")
        for j, h3_title in enumerate(h2_item.get("h3", []), 1):
            print(f"    h3[{j}]: {h3_title}")
    
    # 검증
    is_valid = validate_outline(fallback, keyword)
    print(f"\n검증 결과: {'✅ 통과' if is_valid else '❌ 실패'}")
    assert is_valid, "폴백 아웃라인도 검증을 통과해야 함"
    
    print("\n✅ 폴백 테스트 완료")


if __name__ == "__main__":
    # 파싱, 검증, 폴백 테스트 (하드코딩)
    test_parse_outline()
    test_parse_markdown_outline()
    test_parse_outline_integration()
    test_validate_outline()
    test_fallback_outline()
    
    # 통합 테스트 (실제 GPT 호출)
    print("\n" + "=" * 60)
    print("실제 GPT 호출 테스트를 진행하시겠습니까? (시간이 걸릴 수 있습니다)")
    print("=" * 60)
    
    try:
        test_outline_generation()
    except Exception as e:
        print(f"\n❌ 통합 테스트 중 오류 발생: {e}")
        logger.error(f"통합 테스트 오류: {e}", exc_info=True)

