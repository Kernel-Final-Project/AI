"""
본문 생성 모듈 빠른 테스트 (다른 키워드로)
"""
from content_ai.content_generator import generate_content
from content_ai.outline_generator import generate_outline
from content_ai.title_generator import generate_title
from utils.logger import logger


def test_different_keywords():
    """다른 키워드로 본문 생성 테스트"""
    test_cases = [
        {
            "keyword": "노트북",
            "product_info": "삼성 갤럭시북, 16GB RAM, 512GB SSD"
        },
        {
            "keyword": "운동화",
            "product_info": "나이키 에어맥스, 쿠셔닝, 발목 보호"
        },
        {
            "keyword": "에어컨",
            "product_info": "LG 휘센 벽걸이형, 18평형, 인버터"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"[테스트 {i}] 키워드: {case['keyword']}")
        print(f"{'='*60}")
        
        keyword = case["keyword"]
        product_info = case["product_info"]
        
        # 제목 생성
        print(f"\n[1] 제목 생성 중...")
        title = generate_title(keyword, product_info)
        if not title:
            print("❌ 제목 생성 실패")
            continue
        print(f"✅ 제목: {title} ({len(title)}자)")
        
        # 아웃라인 생성
        print(f"\n[2] 아웃라인 생성 중...")
        outline = generate_outline(keyword, title, product_info)
        if not outline or "h2" not in outline:
            print("❌ 아웃라인 생성 실패")
            continue
        print(f"✅ 아웃라인: h2 {len(outline['h2'])}개")
        
        # 본문 생성
        print(f"\n[3] 본문 생성 중...")
        content = generate_content(keyword, title, outline, product_info)
        
        if content:
            content_length = len(content)
            print(f"✅ 본문 생성 완료: {content_length}자")
            
            # 범위 확인
            if 1500 <= content_length <= 1800:
                print(f"✅ 글자수 범위 통과 (1500~1800자)")
            elif content_length < 1500:
                print(f"⚠️ 글자수 부족 (1500자 미만)")
            else:
                print(f"⚠️ 글자수 초과 (1800자 초과)")
            
            # h2 태그 확인
            h2_count = content.count("<h2>") + content.count("<h2 ")
            print(f"h2 태그: {h2_count}개")
        else:
            print("❌ 본문 생성 실패")


if __name__ == "__main__":
    test_different_keywords()

