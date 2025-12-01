"""
카테고리 메뉴 클릭 및 submenu 감지 모듈
카테고리 메뉴를 클릭하고 submenu가 열릴 때까지 wait하며, 실패 시 fallback 처리
"""
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import time

from utils.logger import logger
from utils.category_patterns import SUBMENU_SELECTORS
from parsers.base.category_interaction import scroll_to_element, hover_element


def click_category_with_fallback(
    driver: webdriver.Chrome,
    element: WebElement,
    timeout: float = 2.0,
    submenu_selectors: Optional[list] = None
) -> Tuple[bool, str]:
    """
    카테고리 메뉴 클릭 → submenu 열릴 때까지 wait → 실패 시 fallback 처리
    
    Args:
        driver: Selenium WebDriver
        element: 클릭할 WebElement
        timeout: submenu 대기 타임아웃 (초)
        submenu_selectors: 커스텀 submenu CSS 선택자 리스트 (선택사항)
        
    Returns:
        (성공 여부, 방법) 튜플
        - (True, "normal_click") - 일반 클릭 성공
        - (True, "js_click") - JS 클릭 성공
        - (True, "hover") - hover 성공
        - (True, "hover_js_click") - hover + JS 클릭 성공
        - (False, "all_methods_failed") - 모든 방법 실패
    """
    # 스크롤 (기존 함수 사용)
    scroll_to_element(driver, element)
    time.sleep(0.3)
    
    # submenu 선택자 설정
    if submenu_selectors is None:
        submenu_selectors = SUBMENU_SELECTORS
    
    # 1) 기본 클릭
    try:
        element.click()
        if _wait_for_submenu_open(driver, element, timeout, submenu_selectors):
            logger.info("카테고리 클릭 성공 (일반 클릭)")
            return True, "normal_click"
    except WebDriverException as e:
        logger.debug(f"일반 클릭 실패: {e}")
    except Exception as e:
        logger.debug(f"일반 클릭 중 오류: {e}")
    
    # 2) JS 강제 클릭
    try:
        driver.execute_script("arguments[0].click();", element)
        if _wait_for_submenu_open(driver, element, timeout, submenu_selectors):
            logger.info("카테고리 클릭 성공 (JS 클릭)")
            return True, "js_click"
    except Exception as e:
        logger.debug(f"JS 클릭 실패: {e}")
    
    # 3) hover 시도 (drop-down 구조일 때)
    try:
        hover_success = hover_element(driver, element, wait_seconds=0.2)
        if hover_success:
            if _wait_for_submenu_open(driver, element, timeout, submenu_selectors):
                logger.info("카테고리 클릭 성공 (hover)")
                return True, "hover"
    except Exception as e:
        logger.debug(f"hover 실패: {e}")
    
    # 4) hover + JS click 조합
    try:
        hover_success = hover_element(driver, element, wait_seconds=0.2)
        if hover_success:
            driver.execute_script("arguments[0].click();", element)
            if _wait_for_submenu_open(driver, element, timeout, submenu_selectors):
                logger.info("카테고리 클릭 성공 (hover + JS 클릭)")
                return True, "hover_js_click"
    except Exception as e:
        logger.debug(f"hover + JS 클릭 실패: {e}")
    
    logger.warning("모든 카테고리 클릭 방법 실패")
    return False, "all_methods_failed"


def _wait_for_submenu_open(
    driver: webdriver.Chrome,
    element: WebElement,
    timeout: float = 2.0,
    submenu_selectors: Optional[list] = None
) -> bool:
    """
    submenu 또는 다음 depth가 열렸는지 확인
    
    Args:
        driver: Selenium WebDriver
        element: 확인할 WebElement
        timeout: 대기 타임아웃 (초)
        submenu_selectors: 커스텀 submenu CSS 선택자 리스트
        
    Returns:
        submenu가 열렸는지 여부 (bool)
    """
    if submenu_selectors is None:
        submenu_selectors = SUBMENU_SELECTORS
    
    try:
        # 1. 요소 내부에서 submenu 찾기
        for selector in submenu_selectors:
            try:
                submenu = element.find_element(By.CSS_SELECTOR, selector)
                # WebDriverWait로 visible 될 때까지 대기
                wait = WebDriverWait(driver, timeout)
                wait.until(EC.visibility_of(submenu))
                logger.debug(f"submenu 감지 성공 (요소 내부): {selector}")
                return True
            except (NoSuchElementException, TimeoutException):
                continue
        
        # 2. 전체 페이지에서 submenu 찾기
        time.sleep(0.2)
        for selector in submenu_selectors:
            try:
                wait = WebDriverWait(driver, timeout)
                submenus = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                # visible한 submenu 찾기
                for submenu in submenus[:3]:  # 상위 3개만 확인
                    try:
                        if submenu.is_displayed():
                            logger.debug(f"submenu 감지 성공 (전체 페이지): {selector}")
                            return True
                    except:
                        continue
            except TimeoutException:
                continue
        
        # 3. 요소의 class/aria 속성 확인
        try:
            class_attr = element.get_attribute("class") or ""
            aria_expanded = element.get_attribute("aria-expanded")
            
            if any(keyword in class_attr.lower() for keyword in ["open", "active", "expanded", "show"]):
                logger.debug("submenu 감지 성공 (class 속성)")
                return True
            
            if aria_expanded == "true":
                logger.debug("submenu 감지 성공 (aria-expanded)")
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        logger.debug(f"submenu 확인 중 오류: {e}")
        return False
