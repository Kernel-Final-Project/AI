"""
싸다구 메뉴 hover 테스트
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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
    driver.get("https://ssadagu.kr")
    print("페이지 로드 대기 중...")
    time.sleep(5)  # 페이지 로드 대기 시간 증가
    
    # 디버깅: 페이지에 어떤 요소가 있는지 확인
    print("\n=== 디버깅: 요소 찾기 시도 ===")
    
    # 방법 1: div.all-cate 찾기
    try:
        all_cate = driver.find_element(By.CSS_SELECTOR, "div.all-cate")
        print("✓ div.all-cate 발견!")
        
        # 내부 요소 확인
        try:
            ico = all_cate.find_element(By.CSS_SELECTOR, ".ico")
            print("✓ .ico 발견!")
        except:
            print("✗ .ico를 찾을 수 없음")
            # 다른 선택자 시도
            try:
                ico = all_cate.find_element(By.CSS_SELECTOR, "span.allc_bt")
                print("✓ span.allc_bt 발견!")
            except:
                print("✗ span.allc_bt도 찾을 수 없음")
    except:
        print("✗ div.all-cate를 찾을 수 없음")
    
    # 방법 2: 직접 선택자 시도
    print("\n직접 선택자 시도...")
    selectors = [
        "div.all_cate .ico",  # 언더스코어 버전
        "div.all-cate .ico",  # 하이픈 버전
        "div.all_cate div.ico",
        "div.all_cate a.ico",
        "div.all_cate span.ico",
        "div.all_cate i.fa-bars",  # 아이콘 직접 찾기
        "span.allc_bt i.fa-bars",  # span 안의 아이콘
        "span.allc_bt",
    ]
    
    icon = None
    for selector in selectors:
        try:
            icon = driver.find_element(By.CSS_SELECTOR, selector)
            print(f"✓ 발견! 선택자: {selector}")
            break
        except:
            print(f"✗ 실패: {selector}")
    
    if not icon:
        print("\n모든 선택자 실패. 페이지 소스 일부 확인...")
        page_source = driver.page_source
        if "all_cate" in page_source or "all-cate" in page_source:
            print("✓ 'all_cate' 또는 'all-cate' 텍스트는 페이지에 존재함")
        if "ico" in page_source:
            print("✓ 'ico' 텍스트는 페이지에 존재함")
        if "allc_bt" in page_source:
            print("✓ 'allc_bt' 텍스트는 페이지에 존재함")
        raise Exception("아이콘 요소를 찾을 수 없습니다")
    
    print("\n아이콘 요소 발견!")
    
    # 요소가 숨겨져 있으면 강제로 표시
    if not icon.is_displayed():
        print("요소가 숨겨져 있음. 강제로 표시 시도...")
        driver.execute_script("arguments[0].style.display = 'block';", icon)
        driver.execute_script("arguments[0].style.visibility = 'visible';", icon)
        time.sleep(0.5)
    
    # 요소가 보이고 상호작용 가능한지 확인
    print(f"요소 표시 여부: {icon.is_displayed()}")
    print(f"요소 크기: {icon.size}")
    print(f"요소 위치: {icon.location}")
    
    # 아이콘 보이게 가져오기 (중앙에 위치)
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", icon
    )
    time.sleep(1)  # 스크롤 완료 대기
    
    # 요소가 상호작용 가능할 때까지 대기
    wait = WebDriverWait(driver, 5)
    wait.until(EC.element_to_be_clickable(icon))
    
    print("요소 상호작용 가능!")
    
    # 아이콘 hover
    print("hover 시도...")
    ActionChains(driver).move_to_element(icon).perform()
    time.sleep(1)
    
    # 메뉴 찾기 (언더스코어 버전 시도)
    try:
        menu = driver.find_element(By.CSS_SELECTOR, "div.all_cate .con_bx")
        print("✓ 메뉴 발견: div.all_cate .con_bx")
    except:
        try:
            menu = driver.find_element(By.CSS_SELECTOR, "div.all-cate .con_bx")
            print("✓ 메뉴 발견: div.all-cate .con_bx")
        except:
            menu = driver.find_element(By.CSS_SELECTOR, ".con_bx")
            print("✓ 메뉴 발견: .con_bx")
    vis = driver.execute_script(
        "return window.getComputedStyle(arguments[0]).visibility;", menu
    )
    
    print("visible ?", vis)
    
    # 결과 확인을 위해 잠시 대기
    print("5초 대기 중... (메뉴 확인)")
    time.sleep(5)
    
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()

