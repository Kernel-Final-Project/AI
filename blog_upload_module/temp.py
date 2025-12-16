import time
import random
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ===== 좌표(네가 확정한 값) =====
TITLE_POS = (1123, 801)  # (참고용) 제목은 DOM 타이핑
BODY_POS = (989, 1010)
PREVIEW_POS = (1861, 314)  # onlineviewer 출력(프리뷰) 텍스트 위


def reset_selection():
    """선택/드래그 꼬임을 풀어주는 최소 동작"""
    pyautogui.press("esc")
    time.sleep(0.05)
    pyautogui.press("right")
    time.sleep(0.05)


def copy_onlineviewer_preview():
    """onlineviewer 프리뷰 영역(리치)을 클립보드로 복사"""
    pyautogui.click(*PREVIEW_POS)
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.10)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.40)


def switch_to_mainframe_if_exists(driver):
    """네이버 글쓰기에서 mainFrame이 있으면 진입"""
    driver.switch_to.default_content()
    try:
        main_frame = driver.find_element(By.ID, "mainFrame")
        driver.switch_to.frame(main_frame)
        return True
    except Exception:
        return False


def close_help_panel_by_escape():
    """네이버 에디터 도움말/팝업이 포커스 잡는 경우가 많아서 ESC 몇 번"""
    for _ in range(3):
        pyautogui.press("esc")
        time.sleep(0.15)


def kill_overlay_layers_js(driver):
    """발행 버튼 클릭을 가로채는 레이어/팝업을 JS로 최대한 제거"""
    try:
        driver.execute_script(
            """
            const selectors = [
              '.se-help-panel',
              '.se-help-panel-wrap',
              '.se-popup',
              '.se-popup-alert',
              '.se-popup-alert-confirm',
              '.se-popup-confirm',
              '[role="dialog"]',
              '.modal',
              '.layer',
              '.dimmed',
              '.dimmed_layer',
              '.dimmed__*'
            ];
            selectors.forEach(sel => {
              document.querySelectorAll(sel).forEach(el => {
                try { el.remove(); } catch(e) {}
              });
            });
            """
        )
    except Exception:
        pass


def find_title_element(driver):
    """
    '제목' 영역을 DOM으로 찾는다.
    (초기 잘 되던 셀렉터들 + role/aria 기반)
    """
    selectors = [
        ".se-section-documentTitle",
        ".se-documentTitle-input",
        "[aria-label='제목']",
        "[data-placeholder*='제목']",
        "input.se-ff-nanummyeongjo",
        # 제목이 contenteditable textbox로 잡히는 경우
        "[contenteditable='true'][role='textbox']",
    ]
    for sel in selectors:
        els = driver.find_elements(By.CSS_SELECTOR, sel)
        for el in els:
            try:
                if el.is_displayed():
                    return el
            except Exception:
                pass
    els = driver.find_elements(
        By.XPATH, "//*[@placeholder and contains(@placeholder,'제목')]"
    )
    for el in els:
        try:
            if el.is_displayed():
                return el
        except Exception:
            pass
    return None


def type_title_with_actionchains(driver, title: str):
    """
    - DOM에서 제목 요소를 찾아 클릭
    - Ctrl+A -> Delete
    - ActionChains.send_keys(title)
    """
    title_el = find_title_element(driver)
    if not title_el:
        raise RuntimeError("제목 입력 요소를 찾을 수 없습니다 (DOM 탐지 실패).")
    title_el.click()
    time.sleep(0.25)
    actions = ActionChains(driver)
    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(
        Keys.DELETE
    ).perform()
    time.sleep(0.10)
    actions.send_keys(title).perform()
    time.sleep(0.40)


def paste_body_rich():
    """본문은 리치 유지가 핵심이라 Ctrl+V"""
    pyautogui.click(*BODY_POS)
    time.sleep(0.25)
    reset_selection()
    # 입력모드 트리거(도움말 드래그/포커스 꼬임 완화)
    pyautogui.press("enter")
    time.sleep(0.08)
    pyautogui.press("up")
    time.sleep(0.08)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1.70)


def safe_click(driver, el):
    """클릭 인터셉트 방지용: 스크롤+JS클릭"""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)


def click_publish(driver):
    """
    :흰색_확인_표시: 발행 로직 (2단계/1단계 모두 대응)
    - 1차 발행: publish_btn__m9KHH or '발행' 텍스트 버튼
    - 최종 발행: confirm_btn__WEaBq or data-testid=seOnePublishBtn
    """
    wait = WebDriverWait(driver, 12)
    # 발행은 종종 overlay가 가림 → 반복적으로 정리
    for _ in range(3):
        close_help_panel_by_escape()
        kill_overlay_layers_js(driver)
        time.sleep(0.3)
    # mainFrame 안쪽에서 버튼이 잡히는 케이스가 많음
    switch_to_mainframe_if_exists(driver)
    # ----------------------
    # 1) "발행"(1차) 버튼
    # ----------------------
    first_candidates = [
        (By.CSS_SELECTOR, "button.publish_btn__m9KHH"),
        (By.XPATH, "//button[.//span[normalize-space()='발행']]"),
        (By.XPATH, "//span[normalize-space()='발행']/ancestor::button[1]"),
    ]
    first_btn = None
    for by, sel in first_candidates:
        try:
            first_btn = wait.until(EC.element_to_be_clickable((by, sel)))
            if first_btn:
                break
        except Exception:
            continue
    if first_btn:
        safe_click(driver, first_btn)
        time.sleep(1.2)
    # ----------------------
    # 2) 최종 발행 버튼
    # ----------------------
    final_candidates = [
        (By.CSS_SELECTOR, "button[data-testid='seOnePublishBtn']"),  # 너가 준 최종 버튼
        (By.CSS_SELECTOR, "button.confirm_btn__WEaBq"),  # 기존 confirm 버튼
        (By.XPATH, "//button[.//span[normalize-space()='발행']]"),
        (By.XPATH, "//span[normalize-space()='발행']/ancestor::button[1]"),
    ]
    final_btn = None
    for by, sel in final_candidates:
        try:
            final_btn = wait.until(EC.element_to_be_clickable((by, sel)))
            if final_btn:
                break
        except Exception:
            continue
    if not final_btn:
        raise RuntimeError(
            "최종 발행 버튼을 찾지 못했습니다 (팝업/레이어로 가려졌을 가능성)."
        )
    safe_click(driver, final_btn)
    time.sleep(2.0)


def upload_to_naver_blog(
    title: str,
    html_content: str,
    naver_id: str,
    naver_pw: str,
    publish: bool = True,
) -> None:
    print("[시작] 네이버 블로그 업로드 플로우 시작")
    if not naver_id or not naver_pw:
        raise ValueError("NAVER_ID / NAVER_PW 환경변수가 비어 있습니다.")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    try:
        # 1) onlineviewer
        print("[1] onlineviewer 접속")
        driver.get("https://html.onlineviewer.net/")
        time.sleep(3)
        print("[2] Ace Editor에 HTML 주입")
        driver.execute_script(
            """
            const ed = window.ace && window.ace.edit("editor");
            if (!ed) throw new Error("Ace editor not found");
            ed.setValue(arguments[0], -1);
            if (typeof previewHtml === 'function') previewHtml();
            """,
            html_content,
        )
        time.sleep(2.5)
        print("[3] onlineviewer 프리뷰 리치 복사")
        copy_onlineviewer_preview()
        print("[4] 리치 텍스트 클립보드 복사 완료")
        # 2) 네이버 로그인
        print("[5] 네이버 로그인")
        driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2.5)
        driver.execute_script(
            """
            document.getElementById('id').value = arguments[0];
            document.getElementById('pw').value = arguments[1];
            """,
            naver_id,
            naver_pw,
        )
        time.sleep(0.3)
        driver.find_element(By.ID, "log.login").click()
        time.sleep(6)
        # 3) 글쓰기
        print("[6] 글쓰기 페이지 이동")
        driver.get("https://blog.naver.com/GoBlogWrite.naver")
        time.sleep(6)
        print("[6-1] mainFrame 진입 시도")
        switch_to_mainframe_if_exists(driver)
        time.sleep(0.8)
        close_help_panel_by_escape()
        kill_overlay_layers_js(driver)
        # 4) 제목
        print("[7] 제목 입력 (ActionChains)")
        type_title_with_actionchains(driver, title)
        print("[7] 제목 입력 완료")
        # 5) 본문
        print("[8] 본문 입력 (리치 붙여넣기)")
        paste_body_rich()
        print("[8] 본문 입력 완료")
        # 6) 발행
        if publish:
            print("[9] 발행 진행")
            click_publish(driver)
            print("[완료] 발행까지 완료")
        else:
            print("[완료] 제목/본문 입력 완료 (발행 미포함)")
    finally:
        # 디버깅 중이면 유지하려면 주석
        # driver.quit()
        pass
