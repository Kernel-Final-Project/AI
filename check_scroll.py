"""
무한 스크롤 확인 스크립트
페이지에 실제로 몇 개의 상품이 있는지, 스크롤을 내리면 더 로드되는지 확인
"""
import sys
from scraper.html_extractor import load_html_ssr, load_html_csr
from scraper.product_parser import detect_product_list, parse_products
from scraper.ssr_csr_checker import check_ssr_csr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
from auto_posting.browser_utils import setup_browser

def check_infinite_scroll(url: str):
    """무한 스크롤 확인"""
    print(f"\n{'='*80}")
    print(f"무한 스크롤 확인: {url}")
    print(f"{'='*80}\n")
    
    # 1. SSR/CSR 판별
    check_result = check_ssr_csr(url)
    print(f"✅ 렌더링 타입: {check_result.rendering_type}\n")
    
    if check_result.rendering_type == "SSR":
        # SSR은 스크롤 없이 바로 확인
        html, soup = load_html_ssr(url)
        product_elements = detect_product_list(soup)
        print(f"📄 첫 페이지 HTML에서 발견된 상품: {len(product_elements)}개")
        return
    
    # 2. CSR 사이트 - 스크롤 테스트
    print("🔍 CSR 사이트 - 스크롤 테스트 시작\n")
    
    driver = setup_browser(headless=True)
    
    try:
        driver.get(url)
        print(f"✅ 페이지 로드 완료")
        
        # 초기 HTML에서 상품 개수 확인
        initial_html = driver.page_source
        initial_soup = BeautifulSoup(initial_html, 'html.parser')
        initial_products = detect_product_list(initial_soup)
        print(f"📄 초기 HTML 상품 수: {len(initial_products)}개")
        
        # 스크롤 전 상품 ID 수집
        initial_product_ids = set()
        for elem in initial_products:
            link = elem.find('a')
            if link:
                href = link.get('href', '')
                if 'num_iid' in href:
                    import re
                    match = re.search(r'num_iid=(\d+)', href)
                    if match:
                        initial_product_ids.add(match.group(1))
        
        print(f"📋 초기 상품 ID 수: {len(initial_product_ids)}개")
        
        # 스크롤 다운 (3번)
        print(f"\n📜 스크롤 다운 시작...")
        for i in range(3):
            # 페이지 끝까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"  스크롤 {i+1}회차 완료")
            time.sleep(2)  # 로딩 대기
            
            # 스크롤 후 상품 개수 확인
            current_html = driver.page_source
            current_soup = BeautifulSoup(current_html, 'html.parser')
            current_products = detect_product_list(current_soup)
            
            # 새로운 상품 ID 수집
            current_product_ids = set()
            for elem in current_products:
                link = elem.find('a')
                if link:
                    href = link.get('href', '')
                    if 'num_iid' in href:
                        match = re.search(r'num_iid=(\d+)', href)
                        if match:
                            current_product_ids.add(match.group(1))
            
            new_products = current_product_ids - initial_product_ids
            print(f"    현재 상품 수: {len(current_products)}개 (새로 추가: {len(new_products)}개)")
            
            if len(new_products) == 0:
                print(f"    ⚠️  더 이상 새로운 상품이 로드되지 않습니다.")
                break
            
            initial_product_ids = current_product_ids
        
        # 최종 결과
        final_html = driver.page_source
        final_soup = BeautifulSoup(final_html, 'html.parser')
        final_products = detect_product_list(final_soup)
        
        print(f"\n📊 최종 결과:")
        print(f"  초기 상품 수: {len(initial_products)}개")
        print(f"  스크롤 후 상품 수: {len(final_products)}개")
        print(f"  증가량: {len(final_products) - len(initial_products)}개")
        
        if len(final_products) > len(initial_products):
            print(f"\n✅ 무한 스크롤 확인: 스크롤을 내리면 더 많은 상품이 로드됩니다!")
        else:
            print(f"\n❌ 무한 스크롤 아님: 페이지에 표시된 상품만 있습니다.")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://ssadagu.kr"
    check_infinite_scroll(url)


