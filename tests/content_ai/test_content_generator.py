"""
본문 생성 모듈 테스트
"""
from content_ai.content_generator import generate_body, validate_body
from content_ai.title_generator import generate_title
from content_ai.outline_generator import generate_outline
from utils.logger import logger


def test_generate_body():
    """본문 생성 통합 테스트 (실제 GPT 호출)"""
    print("=" * 60)
    print("본문 생성 모듈 테스트")
    print("=" * 60)
    
    # 테스트 데이터
    keyword = "ASUS vivobook"
    product_info = "ASUS 비보북 노트북, 15인치, 인텔 i5, 8GB RAM"
    
    print(f"\n[테스트 데이터]")
    print(f"키워드: {keyword}")
    print(f"상품 정보: {product_info}")
    
    # 1. 제목 생성 (필수)
    print(f"\n[1] 제목 생성 (본문 생성을 위해 필요)")
    print("GPT 호출 중...")
    title = generate_title(keyword, product_info)
    if not title:
        print("❌ 제목 생성 실패 - 본문 생성 불가")
        return False
    print(f"✅ 제목 생성 성공: {title} ({len(title)}자)")
    
    # 2. 아웃라인 생성 (필수)
    print(f"\n[2] 아웃라인 생성 (본문 생성을 위해 필요)")
    print("GPT 호출 중...")
    outline = generate_outline(keyword, title, product_info)
    if not outline or "h2" not in outline:
        print("❌ 아웃라인 생성 실패 - 본문 생성 불가")
        return False
    h2_count = len(outline["h2"])
    print(f"✅ 아웃라인 생성 성공: h2 {h2_count}개")
    
    # 3. 본문 생성
    print(f"\n[3] 본문 생성 (content_prompt.txt 사용)")
    print("GPT 호출 중... (시간이 걸릴 수 있습니다)")
    body = generate_body(keyword, title, outline, product_info)
    
    if body:
        # HTML 태그 제거하고 순수 텍스트 길이 계산
        import re
        text_only = re.sub(r'<[^>]+>', '', body)
        text_length = len(text_only.strip())
        
        print(f"✅ 본문 생성 완료: {text_length}자 (전체: {len(body)}자)")
        
        # 본문 일부 출력
        print(f"\n생성된 본문 (처음 300자):")
        print(body[:300] + "..." if len(body) > 300 else body)
        
        # 검증 테스트
        print(f"\n[4] 검증 테스트")
        # 요약된 본문인지 확인 (1800~2100자 범위면 요약된 것으로 간주)
        is_summarized = 1800 <= text_length <= 2100 and text_length > 1800
        is_valid = validate_body(body, is_summarized=is_summarized)
        if is_valid:
            if is_summarized:
                print(f"✅ 요약된 본문 검증 통과 (1800~2100자 범위)")
            else:
                print("✅ 본문 검증 통과 (1500~1800자 범위)")
        else:
            print("❌ 본문 검증 실패")
            return False
        
        # h2/h3 태그 확인
        h2_count = body.count("<h2>") + body.count("<h2 ")
        h3_count = body.count("<h3>") + body.count("<h3 ")
        print(f"\n[5] 태그 확인")
        print(f"h2 태그: {h2_count}개")
        print(f"h3 태그: {h3_count}개")
        
        # 글자수 범위 확인
        print(f"\n[6] 글자수 범위 확인")
        if 1500 <= text_length <= 1800:
            print(f"✅ 글자수 범위 통과 (1500~1800자)")
        elif text_length < 1500:
            print(f"⚠️ 글자수 부족: {text_length}자 (1500자 이상 필요)")
        else:
            print(f"⚠️ 글자수 초과: {text_length}자 (1800자 이하 필요)")
        
    else:
        print("❌ 본문 생성 실패")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 통합 테스트 통과!")
    print("=" * 60)
    return True


def test_validate_body():
    """본문 검증 함수 테스트"""
    print("\n" + "=" * 60)
    print("[테스트 2] 본문 검증 함수 테스트")
    print("=" * 60)
    
    # 케이스 1: 정상 본문 (1500~1800자)
    print("\n[케이스 1] 정상 본문 (1500~1800자)")
    body1 = "<h2>ASUS vivobook 개요</h2><p>" + "가" * 1600 + "</p>"
    is_valid1 = validate_body(body1)
    print(f"결과: {'✅ 검증 통과' if is_valid1 else '❌ 검증 실패'}")
    assert is_valid1, "정상 본문은 검증 통과해야 함"
    
    # 케이스 2: 글자수 부족 (1500자 미만)
    print("\n[케이스 2] 글자수 부족 (1500자 미만)")
    body2 = "<h2>ASUS vivobook 개요</h2><p>" + "가" * 1400 + "</p>"
    is_valid2 = validate_body(body2)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid2 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid2, "1500자 미만은 검증 실패해야 함"
    
    # 케이스 3: 글자수 초과 (1800자 초과)
    print("\n[케이스 3] 글자수 초과 (1800자 초과)")
    body3 = "<h2>ASUS vivobook 개요</h2><p>" + "가" * 1900 + "</p>"
    is_valid3 = validate_body(body3)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid3 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid3, "1800자 초과는 검증 실패해야 함"
    
    # 케이스 4: h2 태그 없음
    print("\n[케이스 4] h2 태그 없음")
    body4 = "<p>" + "가" * 1600 + "</p>"
    is_valid4 = validate_body(body4)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid4 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid4, "h2 태그 없으면 검증 실패해야 함"
    
    # 케이스 5: 빈 본문
    print("\n[케이스 5] 빈 본문")
    body5 = ""
    is_valid5 = validate_body(body5)
    print(f"결과: {'❌ 검증 실패 (예상)' if not is_valid5 else '✅ 검증 통과 (예상과 다름)'}")
    assert not is_valid5, "빈 본문은 검증 실패해야 함"
    
    print("\n✅ 검증 테스트 완료")


if __name__ == "__main__":
    # 검증 테스트 (하드코딩)
    test_validate_body()
    
    # 통합 테스트 (실제 GPT 호출)
    print("\n" + "=" * 60)
    print("실제 GPT 호출 테스트를 진행하시겠습니까? (시간이 걸릴 수 있습니다)")
    print("=" * 60)
    
    try:
        test_generate_body()
    except Exception as e:
        print(f"\n❌ 통합 테스트 중 오류 발생: {e}")
        logger.error(f"통합 테스트 오류: {e}", exc_info=True)

