"""
본문 생성 모듈 테스트
"""
from content_ai.content_generator import (
    generate_content,
    generate_content_text,
    validate_content,
    create_fallback_content
)
from content_ai.outline_generator import generate_outline
from content_ai.title_generator import generate_title
from utils.logger import logger


def test_content_generation():
    """본문 생성 통합 테스트 (실제 GPT 호출)"""
    print("=" * 60)
    print("본문 생성 모듈 테스트")
    print("=" * 60)
    
    # 테스트 데이터
    keyword = "요가매트"
    product_info = "싸다구 프리미엄 요가매트, 두께 10mm, 미끄럼 방지"
    
    print(f"\n[테스트 데이터]")
    print(f"키워드: {keyword}")
    print(f"상품 정보: {product_info}")
    
    # 1. 제목 생성
    print(f"\n[1] 제목 생성")
    print("GPT 호출 중...")
    title = generate_title(keyword, product_info)
    if title:
        print(f"✅ 제목 생성 성공: {title} ({len(title)}자)")
    else:
        print("❌ 제목 생성 실패")
        return False
    
    # 2. 아웃라인 생성
    print(f"\n[2] 아웃라인 생성")
    print("GPT 호출 중...")
    outline = generate_outline(keyword, title, product_info)
    if outline and "h2" in outline:
        h2_count = len(outline["h2"])
        print(f"✅ 아웃라인 생성 성공: h2 {h2_count}개")
    else:
        print("❌ 아웃라인 생성 실패")
        return False
    
    # 3. 본문 생성
    print(f"\n[3] 본문 생성")
    print("GPT 호출 중... (시간이 걸릴 수 있습니다)")
    content = generate_content(keyword, title, outline, product_info)
    
    if content:
        content_length = len(content)
        print(f"✅ 본문 생성 성공: {content_length}자")
        
        # 본문 일부 출력
        print(f"\n생성된 본문 (처음 300자):")
        print(content[:300] + "..." if len(content) > 300 else content)
        
        # 검증 테스트
        print(f"\n[4] 검증 테스트")
        is_valid = validate_content(content)
        if is_valid:
            print("✅ 본문 검증 통과")
        else:
            print("❌ 본문 검증 실패")
            return False
        
        # h2/h3 태그 확인
        h2_count = content.count("<h2>") + content.count("<h2 ")
        h3_count = content.count("<h3>") + content.count("<h3 ")
        print(f"\n[5] 태그 확인")
        print(f"h2 태그: {h2_count}개")
        print(f"h3 태그: {h3_count}개")
        
    else:
        print("❌ 본문 생성 실패")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 통합 테스트 통과!")
    print("=" * 60)
    return True


def test_validate_content():
    """검증 함수 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 2] 검증 함수 테스트")
    print("=" * 60)
    
    # 케이스 1: 정상 본문 (2100~2300자)
    print("\n[케이스 1] 정상 본문")
    content1 = "<h2>요가매트 개요</h2><p>" + "가" * 2200 + "</p>"
    is_valid1 = validate_content(content1)
    print(f"결과: {'✅ 검증 통과' if is_valid1 else '❌ 검증 실패'}")
    assert is_valid1, "정상 본문은 검증 통과해야 함"
    
    # 케이스 2: 글자수 부족 (2100자 미만)
    print("\n[케이스 2] 글자수 부족 (2100자 미만)")
    content2 = "<h2>요가매트 개요</h2><p>" + "가" * 2050 + "</p>"
    is_valid2 = validate_content(content2)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid2 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid2, "2100자 미만은 검증 실패해야 함"
    
    # 케이스 3: 글자수 초과 (2300자 초과)
    print("\n[케이스 3] 글자수 초과 (2300자 초과)")
    content3 = "<h2>요가매트 개요</h2><p>" + "가" * 2350 + "</p>"
    is_valid3 = validate_content(content3)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid3 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid3, "2300자 초과는 검증 실패해야 함"
    
    # 케이스 4: h2 태그 없음
    print("\n[케이스 4] h2 태그 없음")
    content4 = "<p>" + "가" * 2200 + "</p>"
    is_valid4 = validate_content(content4)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid4 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid4, "h2 태그 없으면 검증 실패해야 함"
    
    # 케이스 5: 빈 본문
    print("\n[케이스 5] 빈 본문")
    content5 = ""
    is_valid5 = validate_content(content5)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid5 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid5, "빈 본문은 검증 실패해야 함"
    
    print("\n✅ 검증 테스트 완료")


def test_fallback_content():
    """폴백 본문 생성 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 3] 폴백 본문 생성 테스트")
    print("=" * 60)
    
    keyword = "요가매트"
    title = "요가매트 추천 가이드"
    outline = {
        "h2": [
            {
                "title": "요가매트 개요 정보",
                "h3": ["요가매트 기본 정보"]
            },
            {
                "title": "요가매트 특징 분석",
                "h3": ["요가매트 주요 특징", "요가매트 장점 분석"]
            }
        ]
    }
    
    fallback = create_fallback_content(keyword, title, outline)
    
    print(f"\n생성된 폴백 본문:")
    print(f"글자수: {len(fallback)}자")
    print(f"\n폴백 본문 내용:")
    print(fallback[:200] + "..." if len(fallback) > 200 else fallback)
    
    # 검증 (폴백은 글자수 제한이 없을 수 있음)
    print(f"\n폴백 본문 확인 완료")
    
    print("\n✅ 폴백 테스트 완료")


if __name__ == "__main__":
    # 검증, 폴백 테스트 (하드코딩)
    test_validate_content()
    test_fallback_content()
    
    # 통합 테스트 (실제 GPT 호출)
    print("\n" + "=" * 60)
    print("실제 GPT 호출 테스트를 진행하시겠습니까? (시간이 걸릴 수 있습니다)")
    print("=" * 60)
    
    try:
        test_content_generation()
    except Exception as e:
        print(f"\n❌ 통합 테스트 중 오류 발생: {e}")
        logger.error(f"통합 테스트 오류: {e}", exc_info=True)

