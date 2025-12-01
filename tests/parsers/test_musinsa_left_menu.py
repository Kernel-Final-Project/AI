"""
무신사 왼쪽 메인 카테고리 목록 찾기
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from auto_posting.browser_utils import setup_browser
from parsers.musinsa.config import BASE_URL, MUSINSA_SELECTORS


def find_left_menu_categories():
    """왼쪽 메인 카테고리 목록 찾기"""
    driver = setup_browser(headless=False)
    
    try:
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 카테고리 메뉴 열기
        wait = WebDriverWait(driver, 5)
        category_icon = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, MUSINSA_SELECTORS["category_icon"]))
        )
        category_icon.click()
        time.sleep(1)
        
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        print("=" * 80)
        print("1. 모든 링크에서 메인 카테고리 후보 찾기")
        print("=" * 80)
        
        # 사용자가 알려준 메인 카테고리 목록
        expected_categories = [
            "뷰티", "신발", "상의", "아우터", "바지", "원피스/스커트", 
            "가방", "패션소품", "속옷/홈웨어", "스포츠/레저", 
            "디지털/라이프", "아울렛", "부티크", "키즈", "어스", 
            "K-커넥트", "유즈드"
        ]
        
        all_links = modal.find_elements(By.TAG_NAME, "a")
        print(f"모달 내 총 링크 개수: {len(all_links)}\n")
        
        found_categories = {}
        
        for category in expected_categories:
            # 정확히 일치하는 링크 찾기
            matching_links = []
            for link in all_links:
                link_text = link.text.strip()
                if link_text == category:
                    matching_links.append(link)
            
            if matching_links:
                found_categories[category] = matching_links
                print(f"✓ '{category}' 발견: {len(matching_links)}개")
                for i, link in enumerate(matching_links, 1):
                    classes = link.get_attribute('class')
                    href = link.get_attribute('href')
                    print(f"  {i}. 클래스: {classes[:80]}...")
                    print(f"     href: {href}")
            else:
                print(f"✗ '{category}' 못 찾음")
        
        print("\n" + "=" * 80)
        print("2. 왼쪽 메뉴 영역 찾기")
        print("=" * 80)
        
        # 모달 내부의 주요 div 구조 확인
        all_divs = modal.find_elements(By.TAG_NAME, "div")
        print(f"모달 내 총 div 개수: {len(all_divs)}")
        
        # 클래스 이름에 "menu", "nav", "list", "category" 등이 포함된 div 찾기
        menu_divs = []
        for div in all_divs:
            classes = div.get_attribute('class')
            if classes:
                class_lower = classes.lower()
                if any(keyword in class_lower for keyword in ['menu', 'nav', 'list', 'category', 'header', 'title']):
                    menu_divs.append(div)
        
        print(f"\n메뉴 관련 div: {len(menu_divs)}개")
        
        # 각 div에서 메인 카테고리 링크 찾기
        for i, div in enumerate(menu_divs[:10], 1):  # 처음 10개만
            links_in_div = div.find_elements(By.TAG_NAME, "a")
            if links_in_div:
                print(f"\n[{i}] div 클래스: {div.get_attribute('class')[:60]}...")
                print(f"    링크 개수: {len(links_in_div)}")
                for link in links_in_div[:5]:  # 처음 5개만
                    text = link.text.strip()
                    if text:
                        print(f"      - '{text}'")
        
        print("\n" + "=" * 80)
        print("3. 특정 클래스 패턴 찾기")
        print("=" * 80)
        
        # CategorySubHeader가 아닌 다른 헤더 클래스 찾기
        all_links_with_classes = modal.find_elements(By.CSS_SELECTOR, "a[class]")
        
        # 클래스 이름 수집
        class_patterns = {}
        for link in all_links_with_classes:
            classes = link.get_attribute('class')
            text = link.text.strip()
            if classes and text in expected_categories:
                # 클래스 이름의 주요 부분 추출
                main_class = classes.split()[0] if classes.split() else classes
                if main_class not in class_patterns:
                    class_patterns[main_class] = []
                class_patterns[main_class].append(text)
        
        print("메인 카테고리 링크의 클래스 패턴:")
        for cls, categories in class_patterns.items():
            print(f"\n  {cls}:")
            for cat in categories:
                print(f"    - {cat}")
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    find_left_menu_categories()


