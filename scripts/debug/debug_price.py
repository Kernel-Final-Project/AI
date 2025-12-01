"""
가격 추출 디버깅 스크립트
실제 HTML 구조를 확인하여 가격이 어떻게 표시되는지 분석
"""
import sys
from parsers.base.html_extractor import load_html_ssr, load_html_csr
from parsers.base.product_parser import detect_product_list, detect_price
from parsers.base.ssr_csr_checker import check_ssr_csr
from bs4 import BeautifulSoup
import re

def debug_price_extraction(url: str):
    """가격 추출 디버깅"""
    print(f"\n{'='*80}")
    print(f"가격 추출 디버깅: {url}")
    print(f"{'='*80}\n")
    
    # 1. HTML 로드
    check_result = check_ssr_csr(url)
    if check_result.rendering_type == "SSR":
        html, soup = load_html_ssr(url)
    else:
        html, soup = load_html_csr(url)
    
    # 2. 상품 리스트 찾기
    product_elements = detect_product_list(soup)
    print(f"✅ 상품 요소 {len(product_elements)}개 발견\n")
    
    if not product_elements:
        print("❌ 상품 요소를 찾을 수 없습니다.")
        return
    
    # 3. 처음 3개 상품의 HTML 구조 확인
    for i, element in enumerate(product_elements[:3], 1):
        print(f"{'─'*80}")
        print(f"상품 {i} 분석")
        print(f"{'─'*80}")
        
        # 전체 텍스트 확인
        full_text = element.get_text(strip=True)
        print(f"\n📝 전체 텍스트 (처음 200자):")
        print(f"   {full_text[:200]}...")
        
        # 가격 패턴 찾기
        price_pattern = r'[\d,]+(?:\s*[원₩$€£¥]|원|₩|\$|€|£|¥)'
        matches = re.findall(price_pattern, full_text)
        print(f"\n🔍 전체 텍스트에서 찾은 가격 패턴:")
        if matches:
            for match in matches:
                print(f"   - {match}")
        else:
            print("   ❌ 가격 패턴을 찾을 수 없음")
        
        # .price, .cost, .amount 클래스 찾기
        print(f"\n🏷️  가격 관련 클래스 요소:")
        price_classes = element.find_all(class_=re.compile(r'price|cost|amount', re.I))
        if price_classes:
            for pc in price_classes:
                text = pc.get_text(strip=True)
                print(f"   - 클래스: {pc.get('class')}")
                print(f"     텍스트: {text}")
                match = re.search(price_pattern, text)
                if match:
                    print(f"     ✅ 가격 발견: {match.group()}")
                else:
                    print(f"     ❌ 가격 패턴 없음")
        else:
            print("   ❌ 가격 관련 클래스 요소 없음")
        
        # 숫자 패턴 찾기 (가격일 가능성)
        print(f"\n💰 숫자 패턴 분석:")
        numbers = re.findall(r'[\d,]+', full_text)
        # 4자리 이상 숫자만 (가격일 가능성)
        price_like_numbers = [n for n in numbers if len(n.replace(',', '')) >= 4]
        if price_like_numbers:
            print(f"   발견된 숫자들: {price_like_numbers[:5]}")
        else:
            print("   ❌ 가격처럼 보이는 숫자 없음")
        
        # HTML 구조 전체 출력 (가격 찾기 위해)
        print(f"\n📄 HTML 구조 전체:")
        html_str = str(element)
        # 가격 관련 키워드가 있는 부분 찾기
        if 'price' in html_str.lower() or '원' in html_str or '₩' in html_str:
            print(f"   가격 관련 키워드 발견!")
        # 숫자와 함께 있는 부분 찾기
        lines = html_str.split('\n')
        for line in lines:
            if re.search(r'[\d,]{4,}', line):  # 4자리 이상 숫자
                print(f"   {line[:200]}")
        
        # detect_price 함수 결과
        detected_price = detect_price(element)
        print(f"\n🎯 detect_price() 결과:")
        if detected_price:
            print(f"   ✅ 추출된 가격: {detected_price}")
        else:
            print(f"   ❌ 가격 추출 실패")
        
        print()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://ssadagu.kr"
    debug_price_extraction(url)

