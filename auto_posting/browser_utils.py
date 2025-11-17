"""
브라우저 유틸리티 모듈
AI2 담당
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from utils.logger import logger


def setup_browser(headless: bool = False) -> webdriver.Chrome:
    """
    Selenium Chrome 브라우저를 설정하고 반환합니다.
    
    Args:
        headless: 헤드리스 모드 여부 (기본값: False - GUI 모드)
        
    Returns:
        설정된 Chrome WebDriver
    """
    logger.info("Chrome 브라우저 설정 시작")
    
    chrome_options = Options()
    if not headless:
        # GUI 모드 (로컬 환경에서 안정적 동작)
        chrome_options.add_argument('--start-maximized')
    
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    logger.info("Chrome 브라우저 설정 완료")
    return driver


def wait_for_element(driver, by, value, timeout: int = 10):
    """
    요소가 나타날 때까지 대기합니다.
    
    Args:
        driver: WebDriver 인스턴스
        by: 요소 찾기 방식
        value: 요소 값
        timeout: 대기 시간 (초)
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located((by, value)))

