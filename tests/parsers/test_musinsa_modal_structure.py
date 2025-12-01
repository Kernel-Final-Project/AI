"""
무신사 모달 구조 확인 스크립트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time

from auto_posting.browser_utils import setup_browser
from parsers.musinsa.config import BASE_URL, MUSINSA_SELECTORS


def inspect_modal_structure():
    """모달 구조 확인"""
    driver = setup_browser(headless=False)
    
    try:
        # 메인 페이지 접속
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 카테고리 메뉴 열기
        wait = WebDriverWait(driver, 5)
        category_icon = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, MUSINSA_SELECTORS["category_icon"]))
        )
        category_icon.click()
        time.sleep(1)
        
        # 모달 찾기
        modal = driver.find_element(By.CSS_SELECTOR, MUSINSA_SELECTORS["category_modal"])
        
        print("=" * 80)
        print("모달 HTML 구조 확인")
        print("=" * 80)
        
        # 모달 내부의 모든 링크 찾기
        all_links = modal.find_elements(By.TAG_NAME, "a")
        print(f"\n모달 내 총 링크 개수: {len(all_links)}")
        
        # "뷰티" 링크 찾기
        beauty_link = None
        for link in all_links:
            link_text = link.text.strip()
            if "뷰티" in link_text:
                print(f"\n'뷰티' 링크 발견:")
                print(f"  텍스트: {link_text}")
                print(f"  href: {link.get_attribute('href')}")
                print(f"  data-category-id: {link.get_attribute('data-category-id')}")
                print(f"  클래스: {link.get_attribute('class')}")
                beauty_link = link
                break
        
        if beauty_link:
            print("\n" + "=" * 80)
            print("'뷰티' 링크에 hover 시도 (클릭하지 않음)")
            print("=" * 80)
            
            # hover 시도
            ActionChains(driver).move_to_element(beauty_link).perform()
            time.sleep(1)
            
            # 모달 내부 다시 확인 (하위 메뉴가 나타났는지)
            updated_links = modal.find_elements(By.TAG_NAME, "a")
            print(f"\nhover 후 모달 내 링크 개수: {len(updated_links)}")
            
            # "스킨케어" 또는 "마스크팩" 찾기
            for link in updated_links:
                link_text = link.text.strip()
                if "스킨케어" in link_text or "마스크팩" in link_text:
                    print(f"\n하위 카테고리 발견: {link_text}")
                    print(f"  href: {link.get_attribute('href')}")
                    print(f"  data-category-id: {link.get_attribute('data-category-id')}")
        
        print("\n" + "=" * 80)
        print("모달 내부 HTML 일부 (처음 2000자)")
        print("=" * 80)
        modal_html = modal.get_attribute('outerHTML')
        print(modal_html[:2000])
        
        input("\n엔터를 눌러 종료...")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    inspect_modal_structure()


