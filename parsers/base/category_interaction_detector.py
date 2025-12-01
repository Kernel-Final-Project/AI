"""
카테고리가 hover 기반인지 click 기반인지 자동 판단하는 기능
"""
from typing import Optional, Tuple
from bs4 import Tag
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import *
import time

from utils.logger import logger
from parsers.base.category_interaction import hover_element, scroll_to_element
# _wait_for_submenu_open은 private 함수이므로 직접 구현
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.category_patterns import SUBMENU_SELECTORS


# ----------------------------------------------------------
# 1. 정적(HTML) 기반 분석
# ----------------------------------------------------------
def static_detect_menu_behavior(tag: Tag) -> Tuple[str, int, int]:
    """
    BeautifulSoup Tag 기준 hover / click 기반을 점수로 예측
    
    Returns:
        (결과, click_score, hover_score) 튜플
        - 결과: "click", "hover", "unknown" 중 하나
    """
    click_score = 0
    hover_score = 0
    
    tag_name = tag.name.lower() if tag.name else ""
    classes = " ".join(tag.get("class", [])).lower()
    element_id = tag.get("id", "").lower()
    onclick = tag.get("onclick", "") or ""
    data_toggle = tag.get("data-toggle", "")
    style = (tag.get("style") or "").replace(" ", "").lower()
    
    # ---------- CLICK 기반 패턴 ----------
    if onclick:
        click_score += 5
    
    if data_toggle in ["dropdown", "toggle", "collapse"]:
        click_score += 4
    
    if "cursor:pointer" in style:
        click_score += 2
    
    if any(k in classes for k in ["toggle", "accordion", "openable"]):
        click_score += 3
    
    if tag.get("role") == "button":
        click_score += 2
    
    # ---------- HOVER 기반 패턴 ----------
    hover_keywords = [
        "submenu", "sub-menu", "category-depth",
        "depth1", "depth2", "depth3", "has-submenu",
        "menu-item-has-children", "dropdown-menu",
    ]
    if any(k in classes for k in hover_keywords):
        hover_score += 4
    
    # 숨겨진 submenu 존재 → hover 기반일 확률 큼
    hidden_keywords = ["display:none", "visibility:hidden", "opacity:0"]
    for child in tag.find_all(["ul", "div"], recursive=True, limit=3):
        style_child = (child.get("style") or "").replace(" ", "").lower()
        if any(h in style_child for h in hidden_keywords):
            hover_score += 3
            break
    
    # aria-haspopup, aria-expanded 체크
    if tag.get("aria-haspopup") == "true":
        hover_score += 2
    
    if tag.get("aria-expanded") is not None:
        click_score += 1  # toggle 가능성
    
    # 최종 판단
    if click_score > hover_score:
        return "click", click_score, hover_score
    elif hover_score > click_score:
        return "hover", click_score, hover_score
    else:
        return "unknown", click_score, hover_score


# ----------------------------------------------------------
# 2. Selenium 동적 분석 (강화된 버전)
# ----------------------------------------------------------
def dynamic_detect_menu_behavior(
    driver: webdriver.Chrome,
    element: WebElement,
    timeout: float = 2.0
) -> str:
    """
    Selenium WebElement 기반 동적 테스트 (강화된 판별 알고리즘)
    - hover 시: bounding box height 증가, aria-expanded 변화 감지
    - click 시: URL 변화, history.pushState 호출, DOM append 감지
    - 모바일 UI일 경우 click 우선
    
    Args:
        driver: Selenium WebDriver
        element: 테스트할 WebElement
        timeout: submenu 대기 타임아웃 (초)
    
    Returns:
        "hover", "click", "unknown" 중 하나
    """
    # ========== 모바일 UI 감지 (모바일이면 click 우선) ==========
    try:
        viewport_width = driver.execute_script("return window.innerWidth;")
        if viewport_width < 768:  # 모바일
            logger.debug(f"모바일 UI 감지 (viewport: {viewport_width}px) → click 우선")
            # 모바일은 hover 불가능하므로 click 테스트만 수행
            try:
                initial_url = driver.current_url
                element.click()
                time.sleep(0.5)
                current_url = driver.current_url
                if current_url != initial_url:
                    logger.debug("동적 분석: click 성공 (모바일, URL 변화)")
                    return "click"
                if _check_submenu_opened(driver, element, timeout):
                    logger.debug("동적 분석: click 성공 (모바일, submenu 감지)")
                    return "click"
            except Exception as e:
                logger.debug(f"모바일 click 테스트 실패: {e}")
            return "unknown"
    except Exception as e:
        logger.debug(f"모바일 감지 중 오류 (무시): {e}")
    
    # 스크롤 (필요시)
    try:
        scroll_to_element(driver, element)
        time.sleep(0.2)
    except:
        pass
    
    # ========== 1) Hover 테스트 (강화된 판별) ==========
    try:
        # hover 전 상태 저장
        before_height = element.rect.get('height', 0)
        before_expanded = element.get_attribute("aria-expanded")
        
        hover_success = hover_element(driver, element, wait_seconds=0.3)
        if hover_success:
            time.sleep(0.3)  # submenu 로딩 대기
            
            # 판별 기준 1: bounding box height 증가
            after_height = element.rect.get('height', 0)
            if after_height > before_height + 5:  # 5px 이상 증가
                logger.debug(f"동적 분석: hover 성공 (bounding box 증가: {before_height} → {after_height})")
                return "hover"
            
            # 판별 기준 2: aria-expanded가 true로 변경
            after_expanded = element.get_attribute("aria-expanded")
            if before_expanded != "true" and after_expanded == "true":
                logger.debug(f"동적 분석: hover 성공 (aria-expanded 변화: {before_expanded} → {after_expanded})")
                return "hover"
            
            # 판별 기준 3: submenu 감지 (기존 로직)
            if _check_submenu_opened(driver, element, timeout):
                logger.debug("동적 분석: hover 성공 (submenu 감지)")
                return "hover"
    except Exception as e:
        logger.debug(f"hover 테스트 실패: {e}")
    
    # hover 후 원래 상태로 복귀 (필요시)
    try:
        # 다른 요소로 이동하여 hover 해제
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver).move_to_element(body).perform()
        time.sleep(0.3)
    except:
        pass
    
    # ========== 2) Click 테스트 (강화된 판별) ==========
    try:
        # click 전 상태 저장
        initial_url = driver.current_url
        
        # history.pushState 감지를 위한 리스너 등록
        driver.execute_script("""
            window._historyChanged = false;
            const originalPushState = history.pushState;
            history.pushState = function() {
                window._historyChanged = true;
                return originalPushState.apply(history, arguments);
            };
            
            const originalReplaceState = history.replaceState;
            history.replaceState = function() {
                window._historyChanged = true;
                return originalReplaceState.apply(history, arguments);
            };
        """)
        
        element.click()
        time.sleep(0.5)
        
        # 판별 기준 1: URL 변화
        current_url = driver.current_url
        if current_url != initial_url:
            logger.debug(f"동적 분석: click 성공 (URL 변화: {initial_url} → {current_url})")
            return "click"
        
        # 판별 기준 2: history.pushState/replaceState 호출
        history_changed = driver.execute_script("return window._historyChanged || false;")
        if history_changed:
            logger.debug("동적 분석: click 성공 (history.pushState/replaceState 호출)")
            return "click"
        
        # 판별 기준 3: DOM append 감지 (MutationObserver)
        try:
            js_code = """
                return new Promise((resolve) => {
                    let hasAppend = false;
                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            if (mutation.addedNodes.length > 0) {
                                hasAppend = true;
                            }
                        });
                    });
                    
                    observer.observe(document.body, { 
                        childList: true, 
                        subtree: true 
                    });
                    
                    setTimeout(() => {
                        observer.disconnect();
                        resolve(hasAppend);
                    }, 500);
                });
            """
            has_append = driver.execute_async_script(js_code)
            if has_append:
                logger.debug("동적 분석: click 성공 (DOM append 감지)")
                return "click"
        except Exception as e:
            logger.debug(f"DOM append 감지 중 오류 (무시): {e}")
        
        # 판별 기준 4: submenu 감지 (기존 로직)
        if _check_submenu_opened(driver, element, timeout):
            logger.debug("동적 분석: click 성공 (submenu 감지)")
            return "click"
    except Exception as e:
        logger.debug(f"click 테스트 실패: {e}")
    
    return "unknown"


# ----------------------------------------------------------
# 3. Selenium WebElement 기반 정적 분석
# ----------------------------------------------------------
def static_detect_menu_behavior_from_element(element: WebElement) -> Tuple[str, int, int]:
    """
    Selenium WebElement 기준 hover / click 기반을 점수로 예측
    
    Returns:
        (결과, click_score, hover_score) 튜플
    """
    click_score = 0
    hover_score = 0
    
    try:
        classes = (element.get_attribute("class") or "").lower()
        element_id = (element.get_attribute("id") or "").lower()
        onclick = element.get_attribute("onclick") or ""
        data_toggle = element.get_attribute("data-toggle") or ""
        style = (element.get_attribute("style") or "").replace(" ", "").lower()
        role = element.get_attribute("role") or ""
        
        # ---------- CLICK 기반 패턴 ----------
        if onclick:
            click_score += 5
        
        if data_toggle in ["dropdown", "toggle", "collapse"]:
            click_score += 4
        
        if "cursor:pointer" in style:
            click_score += 2
        
        if any(k in classes for k in ["toggle", "accordion", "openable"]):
            click_score += 3
        
        if role == "button":
            click_score += 2
        
        # ---------- HOVER 기반 패턴 ----------
        hover_keywords = [
            "submenu", "sub-menu", "category-depth",
            "depth1", "depth2", "depth3", "has-submenu",
            "menu-item-has-children", "dropdown-menu",
        ]
        if any(k in classes for k in hover_keywords):
            hover_score += 4
        
        # aria-haspopup, aria-expanded 체크
        aria_haspopup = element.get_attribute("aria-haspopup")
        aria_expanded = element.get_attribute("aria-expanded")
        
        if aria_haspopup == "true":
            hover_score += 2
        
        if aria_expanded is not None:
            click_score += 1  # toggle 가능성
        
        # 최종 판단
        if click_score > hover_score:
            return "click", click_score, hover_score
        elif hover_score > click_score:
            return "hover", click_score, hover_score
        else:
            return "unknown", click_score, hover_score
            
    except Exception as e:
        logger.debug(f"정적 분석 중 오류: {e}")
        return "unknown", 0, 0


# ----------------------------------------------------------
# 4. 통합 판별 함수 (캐싱 지원)
# ----------------------------------------------------------
# 동적 분석 결과 캐싱 (속도 최적화)
_behavior_cache = {}

def detect_menu_behavior(
    driver: Optional[webdriver.Chrome] = None,
    bs4_tag: Optional[Tag] = None,
    selenium_element: Optional[WebElement] = None,
    use_dynamic: bool = True
) -> str:
    """
    BeautifulSoup Tag + Selenium WebElement 둘 다 고려하여
    hover / click / unknown 결정 (캐싱 지원)
    
    Args:
        driver: Selenium WebDriver (동적 분석용, 선택사항)
        bs4_tag: BeautifulSoup Tag 객체 (정적 분석용, 선택사항)
        selenium_element: Selenium WebElement (정적/동적 분석용, 선택사항)
        use_dynamic: 동적 분석 사용 여부
    
    Returns:
        "hover", "click", "unknown" 중 하나
    """
    # 캐시 키 생성 (속도 최적화)
    cache_key = None
    if bs4_tag:
        tag_name = bs4_tag.name or ""
        classes = tuple(bs4_tag.get("class", []))
        element_id = bs4_tag.get("id", "")
        cache_key = f"{tag_name}_{classes}_{element_id}"
    elif selenium_element:
        try:
            tag_name = selenium_element.tag_name or ""
            classes = tuple((selenium_element.get_attribute("class") or "").split())
            element_id = selenium_element.get_attribute("id") or ""
            cache_key = f"{tag_name}_{classes}_{element_id}"
        except:
            pass
    
    # 캐시 확인
    if cache_key and cache_key in _behavior_cache:
        cached_result = _behavior_cache[cache_key]
        logger.debug(f"캐시에서 결과 반환: {cached_result} (키: {cache_key[:50]})")
        return cached_result
    
    static_result = "unknown"
    click_score = 0
    hover_score = 0
    
    # 1) 정적 분석 (BeautifulSoup 기반)
    if bs4_tag:
        static_result, click_score, hover_score = static_detect_menu_behavior(bs4_tag)
        logger.debug(f"정적 분석 (BS4): {static_result} (click={click_score}, hover={hover_score})")
    
    # 2) 정적 분석 (Selenium WebElement 기반)
    elif selenium_element:
        static_result, click_score, hover_score = static_detect_menu_behavior_from_element(selenium_element)
        logger.debug(f"정적 분석 (Selenium): {static_result} (click={click_score}, hover={hover_score})")
    
    # 3) 동적 분석 (Selenium 기반, 우선순위 높음)
    dynamic_result = "unknown"
    if use_dynamic and driver and selenium_element:
        try:
            dynamic_result = dynamic_detect_menu_behavior(driver, selenium_element)
            logger.debug(f"동적 분석: {dynamic_result}")
        except Exception as e:
            logger.debug(f"동적 분석 실패: {e}")
    
    # 4) 최종 결정 로직
    # 동적 분석이 최우선 (가장 정확)
    if dynamic_result != "unknown":
        final_result = dynamic_result
        logger.info(f"메뉴 동작 방식 결정: {final_result} (동적 분석)")
    # 그 다음 정적 분석
    elif static_result != "unknown":
        final_result = static_result
        logger.info(f"메뉴 동작 방식 결정: {final_result} (정적 분석, click={click_score}, hover={hover_score})")
    # 모두 실패
    else:
        final_result = "unknown"
        logger.warning("메뉴 동작 방식 판별 실패: unknown")
    
    # 캐시 저장
    if cache_key:
        _behavior_cache[cache_key] = final_result
    
    return final_result


def _check_submenu_opened(
    driver: webdriver.Chrome,
    element: WebElement,
    timeout: float = 2.0
) -> bool:
    """
    submenu가 열렸는지 확인 (강화된 버전)
    - DOM 변화 감지 (childElementCount 증가)
    - boundingBox (height/width 증가) 감지
    - JS 리스너 이벤트 감지
    - 기존 CSS 선택자 및 속성 체크
    
    Args:
        driver: Selenium WebDriver
        element: 확인할 WebElement
        timeout: 대기 타임아웃 (초)
    
    Returns:
        submenu가 열렸는지 여부 (bool)
    """
    try:
        # ========== 방법 1: DOM 변화 감지 (childElementCount 증가) ==========
        try:
            before_count = len(element.find_elements(By.XPATH, "./*"))
            time.sleep(0.3)  # submenu 생성 대기
            after_count = len(element.find_elements(By.XPATH, "./*"))
            if after_count > before_count:
                logger.debug(f"submenu 감지 성공 (DOM 변화: {before_count} → {after_count})")
                return True
        except Exception as e:
            logger.debug(f"DOM 변화 감지 중 오류 (무시): {e}")
        
        # ========== 방법 2: boundingBox (height/width 증가) 감지 ==========
        try:
            before_rect = element.rect
            before_height = before_rect.get('height', 0)
            before_width = before_rect.get('width', 0)
            time.sleep(0.3)  # submenu 생성 대기
            after_rect = element.rect
            after_height = after_rect.get('height', 0)
            after_width = after_rect.get('width', 0)
            
            # 높이 또는 너비가 10px 이상 증가하면 submenu가 나타난 것으로 판단
            if after_height > before_height + 10 or after_width > before_width + 10:
                logger.debug(f"submenu 감지 성공 (boundingBox: h={before_height}→{after_height}, w={before_width}→{after_width})")
                return True
        except Exception as e:
            logger.debug(f"boundingBox 감지 중 오류 (무시): {e}")
        
        # ========== 방법 3: JS 리스너 이벤트 감지 (MutationObserver) ==========
        try:
            js_code = """
                return new Promise((resolve) => {
                    const target = arguments[0];
                    let hasChanges = false;
                    
                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            if (mutation.addedNodes.length > 0 || mutation.type === 'childList') {
                                hasChanges = true;
                            }
                        });
                    });
                    
                    observer.observe(target, { 
                        childList: true, 
                        subtree: true,
                        attributes: true,
                        attributeFilter: ['class', 'style', 'aria-expanded']
                    });
                    
                    setTimeout(() => {
                        observer.disconnect();
                        resolve(hasChanges);
                    }, 500);
                });
            """
            has_changes = driver.execute_async_script(js_code, element)
            if has_changes:
                logger.debug("submenu 감지 성공 (JS MutationObserver)")
                return True
        except Exception as e:
            logger.debug(f"JS 리스너 감지 중 오류 (무시): {e}")
        
        # ========== 방법 4: 기존 CSS 선택자 기반 탐지 (요소 내부) ==========
        for selector in SUBMENU_SELECTORS:
            try:
                submenu = element.find_element(By.CSS_SELECTOR, selector)
                # WebDriverWait로 visible 될 때까지 대기
                wait = WebDriverWait(driver, timeout)
                wait.until(EC.visibility_of(submenu))
                logger.debug(f"submenu 감지 성공 (요소 내부): {selector}")
                return True
            except (NoSuchElementException, TimeoutException):
                continue
        
        # ========== 방법 5: 전체 페이지에서 submenu 찾기 ==========
        time.sleep(0.2)
        for selector in SUBMENU_SELECTORS:
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
        
        # ========== 방법 6: 요소의 class/aria 속성 확인 ==========
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

