"""
상품 코드 추출 가능성 검토 스크립트
실제 HTML에서 상품 코드가 어떻게 표시되는지 확인
"""
import sys
import re
from scraper.html_extractor import load_html_ssr, load_html_csr
from scraper.product_parser import detect_product_list
from scraper.ssr_csr_checker import check_ssr_csr
from bs4 import BeautifulSoup

def check_product_code(url: str):
    """상품 코드 추출 가능성 검토"""
    print(f"\n{'='*80}")
    print(f"상품 코드 추출 가능성 검토: {url}")
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
    
    # 3. 처음 3개 상품의 HTML 구조에서 상품 코드 찾기
    print(f"{'─'*80}")
    print("상품 코드 추출 가능성 분석")
    print(f"{'─'*80}\n")
    
    for i, element in enumerate(product_elements[:3], 1):
        print(f"[상품 {i}]")
        html_str = str(element)
        
        # 1. 링크 URL에서 상품 코드 추출 시도
        links = element.find_all('a', href=True)
        product_codes_from_url = []
        for link in links:
            href = link.get('href', '')
            # 다양한 패턴 시도
            patterns = [
                r'num_iid=(\d+)',      # 싸다구: num_iid=846537789890
                r'product_id=(\d+)',   # product_id=12345
                r'id=(\d+)',           # id=12345
                r'item_id=(\d+)',      # item_id=12345
                r'goods_id=(\d+)',     # goods_id=12345
                r'/product/(\d+)',     # /product/12345
                r'/item/(\d+)',        # /item/12345
                r'g-(\d+)',            # Temu: g-601101921767940
            ]
            for pattern in patterns:
                match = re.search(pattern, href)
                if match:
                    product_codes_from_url.append(match.group(1))
                    break
        
        if product_codes_from_url:
            print(f"  ✅ URL에서 발견: {product_codes_from_url[0]}")
        else:
            print(f"  ❌ URL에서 상품 코드 없음")
        
        # 2. data 속성에서 상품 코드 찾기
        data_attrs = []
        for attr in element.attrs:
            if 'id' in attr.lower() or 'code' in attr.lower() or 'sku' in attr.lower():
                value = element.get(attr, '')
                if value:
                    data_attrs.append(f"{attr}={value}")
        
        if data_attrs:
            print(f"  ✅ data 속성에서 발견: {', '.join(data_attrs[:3])}")
        else:
            print(f"  ❌ data 속성에 상품 코드 없음")
        
        # 3. input hidden 필드에서 찾기
        hidden_inputs = element.find_all('input', {'type': 'hidden'})
        product_codes_from_input = []
        for inp in hidden_inputs:
            name = inp.get('name', '').lower()
            value = inp.get('value', '')
            if any(keyword in name for keyword in ['id', 'code', 'sku', 'item', 'product']):
                if value and value.isdigit():
                    product_codes_from_input.append(f"{name}={value}")
        
        if product_codes_from_input:
            print(f"  ✅ hidden input에서 발견: {', '.join(product_codes_from_input[:2])}")
        else:
            print(f"  ❌ hidden input에 상품 코드 없음")
        
        # 4. 클래스명이나 ID에서 찾기
        class_names = element.get('class', [])
        elem_id = element.get('id', '')
        if elem_id:
            # ID에서 숫자 추출
            id_match = re.search(r'(\d+)', elem_id)
            if id_match:
                print(f"  ✅ 요소 ID에서 발견: {elem_id} → {id_match.group(1)}")
        
        # 5. HTML 구조 일부 출력 (상품 코드 관련 부분)
        print(f"\n  📄 관련 HTML 구조:")
        lines = html_str.split('\n')
        code_related = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ['id', 'code', 'sku', 'num_iid', 'product_id']):
                code_related.append(line.strip()[:150])
        
        if code_related:
            for line in code_related[:3]:
                print(f"    {line}")
        else:
            print(f"    (상품 코드 관련 HTML 없음)")
        
        print()
    
    print(f"{'─'*80}")
    print("결론:")
    print("  - URL에서 상품 코드 추출: 가장 일반적이고 안정적")
    print("  - data 속성: 일부 사이트에서 사용")
    print("  - hidden input: 폼 기반 사이트에서 사용")
    print("  - 요소 ID: 드물지만 가능")
    print(f"{'─'*80}")

if __name__ == "__main__":
    urls = [
        "https://ssadagu.kr",
        "https://www.temu.com/ul/kuiper/un2.html?_p_rfs=1&subj=un-search-web&_p_jump_id=960&_x_vst_scene=adg&search_key=%EC%9D%B8%ED%84%B0%EB%84%B7%EC%87%BC%ED%95%91%EB%AA%B0&_x_ads_channel=google&_x_ads_sub_channel=search&adg_ctx=m-7b0028eb~f-f0dedbbb&_x_ads_account=5250771380&_x_ads_set=23255253592&_x_ads_id=194148473408&_x_ads_creative_id=783482273937&_x_ns_source=g&_x_ns_match_type=b&_x_ns_keyword=%EC%9D%B8%ED%84%B0%EB%84%B7%EC%87%BC%ED%95%91%EB%AA%B0&_x_ns_targetid=kwd-1747446970&gad_source=1&gad_campaignid=23255253592&gbraid=0AAAAAo4mICGt7vX2tS9Z4A_4CToGAqqHx&gclid=CjwKCAiAlfvIBhA6EiwAcErpyYBTc3GqXz-VZFUw8Zf9gzu7UvuhAHRjL-Qnty3UfJbvZ-5JxJI8ORoCTj4QAvD_BwE"
    ]
    
    url = sys.argv[1] if len(sys.argv) > 1 else urls[0]
    check_product_code(url)


