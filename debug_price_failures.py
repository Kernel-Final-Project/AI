"""
가격 추출 실패 원인 분석 스크립트
가격을 추출하지 못한 상품들을 찾아 원인 분석
"""
import sys
from scraper.html_extractor import load_html_ssr, load_html_csr
from scraper.product_parser import detect_product_list, detect_price, extract_product_info
from scraper.ssr_csr_checker import check_ssr_csr
from bs4 import BeautifulSoup
import re

def analyze_price_failures(url: str):
    """가격 추출 실패 원인 분석"""
    print(f"\n{'='*80}")
    print(f"가격 추출 실패 원인 분석: {url}")
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
    
    # 3. 각 상품의 가격 추출 시도 및 실패 원인 분석
    failed_products = []
    success_count = 0
    
    for i, element in enumerate(product_elements):
        product = extract_product_info(element, url)
        if not product or not product.title:
            continue
        
        if not product.price:
            failed_products.append((i, element, product))
        else:
            success_count += 1
    
    print(f"✅ 가격 추출 성공: {success_count}개")
    print(f"❌ 가격 추출 실패: {len(failed_products)}개\n")
    
    if not failed_products:
        print("🎉 모든 상품의 가격을 성공적으로 추출했습니다!")
        return
    
    # 4. 실패한 상품들 상세 분석
    print(f"{'='*80}")
    print(f"실패한 상품 상세 분석 ({len(failed_products)}개)")
    print(f"{'='*80}\n")
    
    for idx, (original_idx, element, product) in enumerate(failed_products[:10], 1):  # 최대 10개만
        print(f"{'─'*80}")
        print(f"실패 상품 {idx} (원본 인덱스: {original_idx})")
        print(f"{'─'*80}")
        print(f"📌 제목: {product.title[:60]}...")
        
        # HTML 구조 확인
        html_str = str(element)
        
        # 1. name="price" input 확인
        price_inputs = element.find_all('input', {'name': re.compile(r'price|cost|amount', re.I)})
        print(f"\n1️⃣ name='price' input 요소:")
        if price_inputs:
            for pi in price_inputs:
                name = pi.get('name', '')
                value = pi.get('value', '')
                print(f"   ✅ 발견: name='{name}', value='{value}'")
                if value:
                    # 숫자 패턴 확인
                    match = re.search(r'[\d,]{4,}', value)
                    if match:
                        print(f"      ✅ 숫자 패턴 매칭: {match.group()}")
                    else:
                        print(f"      ❌ 숫자 패턴 매칭 실패 (값: '{value}')")
        else:
            print("   ❌ 없음")
        
        # 2. class에 price 포함된 요소 확인
        print(f"\n2️⃣ class에 'price' 포함된 요소:")
        price_class_elements = element.find_all(class_=re.compile(r'price|cost|amount', re.I))
        if price_class_elements:
            for pce in price_class_elements:
                classes = pce.get('class', [])
                text = pce.get_text(strip=True)
                print(f"   ✅ 발견: class={classes}, text='{text[:50]}'")
                
                # 가격 패턴 확인
                price_pattern = r'[\d,]+(?:\s*[원₩$€£¥]|원|₩|\$|€|£|¥)'
                match1 = re.search(price_pattern, text)
                if match1:
                    print(f"      ✅ 통화 기호 포함 패턴: {match1.group()}")
                else:
                    match2 = re.search(r'[\d,]{4,}', text)
                    if match2:
                        print(f"      ✅ 숫자만 패턴: {match2.group()}")
                    else:
                        print(f"      ❌ 가격 패턴 없음")
        else:
            print("   ❌ 없음")
        
        # 3. 전체 텍스트에서 숫자 패턴 확인
        print(f"\n3️⃣ 전체 텍스트 분석:")
        full_text = element.get_text()
        numbers = re.findall(r'[\d,]{4,}', full_text)
        if numbers:
            print(f"   발견된 숫자들: {numbers[:5]}")
            # 가격일 가능성 있는 숫자 필터링
            price_like = [n for n in numbers if len(n.replace(',', '')) >= 4]
            if price_like:
                print(f"   💰 가격처럼 보이는 숫자: {price_like[:3]}")
            else:
                print(f"   ❌ 가격처럼 보이는 숫자 없음")
        else:
            print("   ❌ 4자리 이상 숫자 없음")
        
        # 4. HTML 구조 일부 출력 (가격 관련 부분)
        print(f"\n4️⃣ HTML 구조 (가격 관련 부분):")
        lines = html_str.split('\n')
        price_related_lines = []
        for line in lines:
            if 'price' in line.lower() or re.search(r'[\d,]{4,}', line):
                price_related_lines.append(line.strip()[:150])
        
        if price_related_lines:
            for line in price_related_lines[:5]:
                print(f"   {line}")
        else:
            print("   ❌ 가격 관련 HTML 없음")
        
        print()
    
    if len(failed_products) > 10:
        print(f"\n  ... 외 {len(failed_products) - 10}개 실패 상품")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://ssadagu.kr"
    analyze_price_failures(url)


