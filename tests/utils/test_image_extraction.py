"""
싸다구 상품 이미지 추출 테스트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# 브라우저 설정
chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 카테고리 페이지로 직접 이동
    url = "https://ssadagu.kr/shop/search.php?ss_tx=%EB%82%A8%EC%84%B1+%EC%85%94%EC%B8%A0"
    driver.get(url)
    time.sleep(3)
    
    # 페이지 로드 대기
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_info"))
    )
    
    # Selenium으로 직접 요소 찾기
    print("\n" + "=" * 60)
    print("Selenium으로 직접 요소 찾기")
    print("=" * 60)
    
    products = driver.find_elements(By.CSS_SELECTOR, "div.product_info")
    print(f"발견된 상품 개수: {len(products)}")
    
    if products:
        first_product = products[0]
        
        # 이미지 찾기
        img_selectors = [
            "img.hover-big",
            "a img",
            "img[class*='hover']",
            "img",
        ]
        
        for selector in img_selectors:
            try:
                imgs = first_product.find_elements(By.CSS_SELECTOR, selector)
                if imgs:
                    print(f"\n✓ 발견! 선택자: {selector} ({len(imgs)}개)")
                    for i, img in enumerate(imgs, 1):
                        src = img.get_attribute('src')
                        data_src = img.get_attribute('data-src')
                        classes = img.get_attribute('class')
                        alt = img.get_attribute('alt')
                        print(f"  [이미지 {i}]")
                        print(f"    src: {src[:100] if src else '없음'}")
                        print(f"    data-src: {data_src[:100] if data_src else '없음'}")
                        print(f"    class: {classes}")
                        print(f"    alt: {alt[:50] if alt else '없음'}")
            except:
                pass
        
        # 상품 요소의 부모 확인
        print("\n" + "=" * 60)
        print("상품 요소의 부모/형제 확인")
        print("=" * 60)
        
        # 부모 요소 확인
        parent = driver.execute_script("return arguments[0].parentElement;", first_product)
        if parent:
            print(f"부모 태그: {parent.tag_name}")
            print(f"부모 클래스: {parent.get_attribute('class')}")
            
            # 부모 내부의 모든 이미지 찾기
            parent_imgs = parent.find_elements(By.CSS_SELECTOR, "img")
            print(f"\n부모 내부 이미지: {len(parent_imgs)}개")
            for i, img in enumerate(parent_imgs, 1):
                src = img.get_attribute('src')
                if src and 'icon' not in src.lower() and 'star' not in src.lower():
                    print(f"  [이미지 {i}] src: {src[:100]}")
                    print(f"    class: {img.get_attribute('class')}")
        
        # 형제 요소 확인
        siblings = driver.execute_script("""
            var parent = arguments[0].parentElement;
            return Array.from(parent.children).filter(function(el) {
                return el !== arguments[0];
            });
        """, first_product)
        
        print(f"\n형제 요소: {len(siblings)}개")
        for i, sibling in enumerate(siblings, 1):
            tag = sibling.tag_name
            classes = sibling.get_attribute('class')
            print(f"  [형제 {i}] {tag}, class: {classes}")
            
            # 형제 내부의 이미지 찾기
            try:
                sibling_imgs = sibling.find_elements(By.CSS_SELECTOR, "img")
                for img in sibling_imgs:
                    src = img.get_attribute('src')
                    if src and 'icon' not in src.lower() and 'star' not in src.lower():
                        print(f"    → 이미지 발견! src: {src[:100]}")
            except:
                pass
        
        # 상품 요소의 outerHTML 확인
        print("\n" + "=" * 60)
        print("첫 번째 상품 outerHTML (처음 1500자)")
        print("=" * 60)
        html = first_product.get_attribute('outerHTML')
        print(html[:1500])
    
    # BeautifulSoup으로도 확인
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # 첫 번째 상품 찾기
    product = soup.select_one("div.product_info")
    if not product:
        print("상품을 찾을 수 없습니다")
    else:
        print("=" * 60)
        print("첫 번째 상품 HTML 구조 분석")
        print("=" * 60)
        
        # 모든 이미지 찾기
        all_imgs = product.find_all("img")
        print(f"\n발견된 모든 이미지: {len(all_imgs)}개")
        
        for i, img in enumerate(all_imgs, 1):
            src = img.get('src', '')
            data_src = img.get('data-src', '')
            classes = img.get('class', [])
            alt = img.get('alt', '')
            
            print(f"\n[이미지 {i}]")
            print(f"  src: {src[:100] if src else '없음'}")
            print(f"  data-src: {data_src[:100] if data_src else '없음'}")
            print(f"  class: {classes}")
            print(f"  alt: {alt[:50] if alt else '없음'}")
            
            # 상품 이미지인지 판단 (별점 아이콘이 아닌 것)
            if src and 'icon' not in src.lower() and 'star' not in src.lower():
                print(f"  → 상품 이미지로 추정!")
        
        # 특정 선택자로 찾기
        print("\n" + "=" * 60)
        print("특정 선택자로 찾기")
        print("=" * 60)
        
        selectors = [
            "img.hover-big",
            "a img.hover-big",
            "a > img",
            "img[src*='alicdn']",
            "img[src*='http']",
        ]
        
        for selector in selectors:
            imgs = product.select(selector)
            if imgs:
                print(f"\n✓ 발견! 선택자: {selector} ({len(imgs)}개)")
                for img in imgs:
                    print(f"  src: {img.get('src', '없음')[:100]}")
        
        # 상품 HTML 구조 일부 출력
        print("\n" + "=" * 60)
        print("상품 HTML 구조 (처음 1000자)")
        print("=" * 60)
        print(str(product)[:1000])
    
    print("\n5초 대기 중...")
    time.sleep(5)
    
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()

