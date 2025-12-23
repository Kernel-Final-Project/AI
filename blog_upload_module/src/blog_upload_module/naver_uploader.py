"""
Standalone Naver blog uploader (copied from auto_posting/naver_uploader.py).
"""

from __future__ import annotations

import platform
import random
import time
import pyautogui
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import build_chrome_driver
from .logger import logger
from .results import UploadResult


_INVALID_SESSION_MESSAGE = (
    "업로드 중 제어 브라우저 연결이 끊겼습니다. 다시 시도하거나 관리자에게 문의해주세요."
)
_GENERIC_BROWSER_ERROR_MESSAGE = (
    "업로드를 진행하던 브라우저 제어에 실패했습니다. 잠시 후 다시 시도해주세요."
)
_UNKNOWN_ERROR_MESSAGE = "네이버 블로그 업로드 중 알 수 없는 오류가 발생했습니다."


class NaverBlogAutomation:
    """
    네이버 블로그 자동 업로드 봇
    - 제목: DOM + ActionChains
    - 본문: HTML -> onlineviewer -> Ctrl+V (리치)
    """

    # ===== pyautogui 좌표 (환경에 맞게 조정된 값) =====
    BODY_POS = (989, 1010)
    PREVIEW_POS = (1861, 314)

    def __init__(
        self,
        *,
        naver_id: str,
        naver_pw: str,
        blog_url: str,
        headless: bool = False,
        wait_time: int = 10,
    ) -> None:
        logger.info("네이버 블로그 자동화 시작")
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.blog_url = blog_url

        try:
            self.driver: webdriver.Chrome = build_chrome_driver(headless=headless)
        except WebDriverException as exc:
            logger.error("Chrome 드라이버 초기화 실패: %s", exc)
            raise

        self.wait = WebDriverWait(self.driver, wait_time)
        self.actions = ActionChains(self.driver)
        self.is_mac = platform.system().lower() == "darwin"
        self.last_post_url: Optional[str] = None

    # ------------------------ 공통 유틸 ------------------------

    def _hotkey(self, *keys):
        """
        ctrl -> mac에서는 command 로 자동 변환
        """
        if self.is_mac:
            keys = tuple("command" if k == "ctrl" else k for k in keys)
        pyautogui.hotkey(*keys)

    def random_sleep(self, a=0.8, b=1.5):
        time.sleep(random.uniform(a, b))

    def human_type_actions(self, text: str):
        """ActionChains로 사람처럼 한 글자씩 입력"""
        for ch in text:
            self.actions.send_keys(ch).perform()
            time.sleep(random.uniform(0.01, 0.10))

    def select_all_and_delete(self):
        """
        현재 포커스된 입력창의 모든 텍스트를 선택 후 삭제
        """
        key_cmd = Keys.COMMAND if self.is_mac else Keys.CONTROL
        self.actions.key_down(key_cmd).send_keys("a").key_up(key_cmd).send_keys(
            Keys.DELETE
        ).perform()
        self.random_sleep(0.3, 0.5)

    # ------------------------ 로그인 ------------------------
    def login(self):
        logger.info("네이버 로그인 시작")
        driver = self.driver
        wait = self.wait

        naver_id = self.naver_id
        naver_pw = self.naver_pw
        blog_url = self.blog_url

        if not naver_id or not naver_pw or not blog_url:
            raise ValueError(
                "NAVER_ID, NAVER_PW, NAVER_BLOG_URL이 설정되지 않았습니다."
            )

        try:
            parsed = urlparse(blog_url.rstrip("/"))
            self.blog_id = parsed.path.strip("/")
            logger.info("블로그 ID 추출: %s", self.blog_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("블로그 URL 파싱 실패 (무시): %s", exc)
            self.blog_id = None

        driver.get("https://nid.naver.com/nidlogin.login")
        self.random_sleep(2, 3)

        id_input = wait.until(EC.presence_of_element_located((By.ID, "id")))
        driver.execute_script(
            """
        var element = arguments[0];
        var value = arguments[1];
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        """,
            id_input,
            naver_id,
        )
        time.sleep(0.5)

        pw_input = wait.until(EC.presence_of_element_located((By.ID, "pw")))
        driver.execute_script(
            """
        var element = arguments[0];
        var value = arguments[1];
        element.value = value;
        element.dispatchEvent(new Event('input', { bubbles: true }));
        element.dispatchEvent(new Event('change', { bubbles: true }));
        """,
            pw_input,
            naver_pw,
        )
        time.sleep(0.5)

        login_btn = wait.until(EC.element_to_be_clickable((By.ID, "log.login")))
        login_btn.click()
        self.random_sleep(3, 4)

        try:
            skip_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), '다음에 하기')]"
            )
            if not skip_buttons:
                skip_buttons = driver.find_elements(
                    By.XPATH, "//button[contains(text(), '취소')]"
                )
            if not skip_buttons:
                skip_buttons = driver.find_elements(
                    By.XPATH, "//button[contains(text(), '나중에')]"
                )
            if not skip_buttons:
                skip_buttons = driver.find_elements(By.CSS_SELECTOR, ".btn_next")

            if skip_buttons:
                skip_buttons[0].click()
                time.sleep(1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("새 브라우저 등록 팝업 처리 중 예외 (무시): %s", exc)

        logger.info("네이버 로그인 완료")

    # ------------------------ 도움말 패널 닫기 ------------------------
    def close_help_panel(self):
        driver = self.driver
        logger.info("도움말 패널 및 팝업 딤 레이어 닫기 시도...")

        # 팝업 딤 레이어 강제 제거
        try:
            driver.execute_script(
                """
            var dims = document.querySelectorAll('.se-popup-dim, .se-popup-dim-white, [class*="popup-dim"]');
            dims.forEach(function(dim) {
                dim.remove();
            });
            """
            )
            time.sleep(0.5)
        except Exception:  # noqa: BLE001
            pass

        try:
            driver.execute_script(
                """
            var btn = document.querySelector('.se-help-panel-close-button');
            if (btn) { btn.click(); return true; } return false;
            """
            )
            time.sleep(1)
        except Exception:  # noqa: BLE001
            pass

        try:
            help_buttons = driver.find_elements(
                By.CSS_SELECTOR, ".se-help-panel-close-button"
            )
            for btn in help_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
        except Exception:  # noqa: BLE001
            pass

        try:
            xpath_buttons = driver.find_elements(
                By.XPATH, "//button[contains(@class, 'se-help-panel-close-button')]"
            )
            for btn in xpath_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1)
        except Exception:  # noqa: BLE001
            pass

        try:
            actions = ActionChains(driver)
            actions.send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except Exception:  # noqa: BLE001
            pass

        logger.info("도움말 패널 및 팝업 딤 레이어 닫기 완료")

    # ------------------------ 글쓰기 페이지 준비 ------------------------
    def prepare_editor(self) -> bool:
        driver = self.driver
        wait = self.wait

        logger.info("글쓰기 페이지 준비 시작")
        driver.get("https://blog.naver.com/GoBlogWrite.naver")
        time.sleep(3)

        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        try:
            driver.switch_to.default_content()
            main_frame = wait.until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            driver.switch_to.frame(main_frame)
            time.sleep(2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mainFrame 전환 실패 (무시): %s", exc)

        self.close_help_panel()

        try:
            continue_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), '새로 작성')]"
            )
            for btn in continue_buttons:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)

            cancel_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), '취소')]"
            )
            for btn in cancel_buttons:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)

            close_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(text(), '시작하기') or contains(text(), '닫기') "
                "or contains(@class, 'close') or contains(@class, 'cancel')]",
            )
            for btn in close_buttons:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("팝업 처리 중 오류 (무시): %s", exc)

        try:
            has_title = driver.execute_script(
                """
            return Boolean(
              document.querySelector('.se-section-documentTitle') ||
              document.querySelector('.se-documentTitle-input') ||
              document.querySelector('.document_title') ||
              document.querySelector('input.se-ff-nanummyeongjo')
            );
            """
            )

            if has_title:
                logger.info("에디터 준비 완료: 제목 필드 확인됨")
                return True

            logger.info("제목 필드를 찾지 못해 도움말 재시도")
            self.close_help_panel()

            has_title = driver.execute_script(
                """
            return Boolean(
              document.querySelector('.se-section-documentTitle') ||
              document.querySelector('.se-documentTitle-input') ||
              document.querySelector('.document_title') ||
              document.querySelector('input.se-ff-nanummyeongjo')
            );
            """
            )

            if has_title:
                logger.info("에디터 준비 완료 (2차 시도에서 제목 필드 발견)")
                return True

            logger.error("제목 필드를 결국 찾지 못했습니다.")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("에디터 준비 상태 확인 중 오류: %s", exc)
            return False

    # ------------------------ 발행 버튼 클릭 ------------------------
    def click_publish(self):
        driver = self.driver
        wait = self.wait

        # ----- 1차 발행 버튼 -----
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

        if not first_btn:
            raise RuntimeError("1차 발행 버튼을 찾지 못했습니다.")

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", first_btn
        )
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", first_btn)
        self.random_sleep(0.8, 1.2)

        # ----- 최종 발행 버튼 -----
        final_candidates = [
            (By.CSS_SELECTOR, "button[data-testid='seOnePublishBtn']"),
            (By.CSS_SELECTOR, "button.confirm_btn__WEaBq"),
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
            raise RuntimeError("최종 발행 버튼을 찾지 못했습니다.")

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", final_btn
        )
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", final_btn)

    # ------------------------------------------------------------------
    # 제목 입력 (DOM)
    # ------------------------------------------------------------------
    def _write_title(self, title: str):
        driver = self.driver

        # 반드시 frame 보정
        driver.switch_to.default_content()
        try:
            frame = driver.find_element(By.ID, "mainFrame")
            driver.switch_to.frame(frame)
        except Exception:
            pass

        time.sleep(0.5)

        # 팝업 딤 레이어 제거 (강화)
        self.close_help_panel()
        time.sleep(0.5)  # 팝업 제거 후 대기 시간 추가

        # 팝업 딤 레이어가 완전히 사라졌는지 확인
        try:
            driver.execute_script(
                """
                var dims = document.querySelectorAll('.se-popup-dim, .se-popup-dim-white, [class*="popup-dim"]');
                if (dims.length > 0) {
                    dims.forEach(function(dim) {
                        dim.style.display = 'none';
                        dim.remove();
                    });
                }
                """
            )
            time.sleep(0.3)
        except Exception:  # noqa: BLE001
            pass

        title_el = None

        # 1️⃣ 최신 네이버용 (가장 중요)
        candidates = driver.find_elements(
            By.XPATH, "//*[@contenteditable='true' and @role='textbox']"
        )
        for el in candidates:
            if el.is_displayed():
                title_el = el
                break

        # 2️⃣ 기존 CSS fallback
        if not title_el:
            selectors = [
                ".se-section-documentTitle",
                ".se-documentTitle-input",
                ".document_title",
                "input.se-ff-nanummyeongjo",
            ]
            for sel in selectors:
                for el in driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed():
                        title_el = el
                        break
                if title_el:
                    break

        # 3️⃣ 최후 XPath fallback
        if not title_el:
            xpath_candidates = driver.find_elements(
                By.XPATH,
                "//*[contains(@placeholder,'제목') or contains(@class,'title')]",
            )
            for el in xpath_candidates:
                if el.is_displayed():
                    title_el = el
                    break

        if not title_el:
            raise RuntimeError("제목 입력 필드를 찾지 못했습니다 (DOM 미생성 상태)")

        # 입력 - JavaScript로 포커스 (팝업 차단 회피)
        try:
            driver.execute_script("arguments[0].focus();", title_el)
            time.sleep(0.3)
        except Exception:  # noqa: BLE001
            title_el.click()
            time.sleep(0.3)

        self.select_all_and_delete()
        self.human_type_actions(title)
        time.sleep(0.4)

    # ------------------------------------------------------------------
    # HTML -> onlineviewer -> 클립보드 복사
    # ------------------------------------------------------------------
    def _copy_html_as_rich(self, html: str):
        driver = self.driver
        logger.info("onlineviewer HTML 변환 시작")

        driver.get("https://html.onlineviewer.net/")
        time.sleep(3)

        driver.execute_script(
            """
            const ed = window.ace && window.ace.edit("editor");
            if (!ed) throw new Error("Ace editor not found");
            ed.setValue(arguments[0], -1);
            if (typeof previewHtml === 'function') previewHtml();
            """,
            html,
        )

        time.sleep(2.5)

        pyautogui.click(*self.PREVIEW_POS)
        time.sleep(0.2)
        self._hotkey("ctrl", "a")
        time.sleep(0.1)
        self._hotkey("ctrl", "c")
        time.sleep(0.5)

        logger.info("리치 HTML 클립보드 복사 완료")

    # ------------------------------------------------------------------
    # 네이버 본문 리치 붙여넣기
    # ------------------------------------------------------------------
    def _paste_body_rich(self):
        logger.info("네이버 본문 리치 붙여넣기")

        pyautogui.click(*self.BODY_POS)
        time.sleep(0.25)

        pyautogui.press("esc")
        time.sleep(0.05)
        pyautogui.press("enter")
        time.sleep(0.05)
        pyautogui.press("up")
        time.sleep(0.1)

        self._hotkey("ctrl", "v")
        time.sleep(1.8)

    def _paste_body_in_naver_blog(self):
        """본문을 네이버 블로그에 붙여넣기 (Selenium 기반)"""
        driver = self.driver

        # 팝업 딤 레이어 제거
        self.close_help_panel()

        # 본문 에디터 영역 찾기
        body_el = None

        # 1️⃣ contenteditable 영역 찾기
        try:
            candidates = driver.find_elements(
                By.CSS_SELECTOR, ".se-component-content[contenteditable='true'], [contenteditable='true'].se-component"
            )
            for el in candidates:
                if el.is_displayed():
                    body_el = el
                    break
        except Exception:  # noqa: BLE001
            pass

        # 2️⃣ 본문 컨테이너 찾기
        if not body_el:
            try:
                selectors = [
                    ".se-main-container",
                    ".se-component-content",
                    ".se-text-paragraph",
                    "#se-main-container"
                ]
                for sel in selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in elements:
                        if el.is_displayed():
                            body_el = el
                            break
                    if body_el:
                        break
            except Exception:  # noqa: BLE001
                pass

        # 본문 영역을 찾았으면 Selenium으로 포커스 및 붙여넣기
        if body_el:
            try:
                logger.info("본문 영역 찾음 - Selenium으로 붙여넣기 시도")
                driver.execute_script("arguments[0].focus();", body_el)
                time.sleep(0.3)

                # ActionChains로 붙여넣기
                key_cmd = Keys.COMMAND if self.is_mac else Keys.CONTROL
                actions = ActionChains(driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.05)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.05)
                actions.send_keys(Keys.UP).perform()
                time.sleep(0.1)
                actions.key_down(key_cmd).send_keys("v").key_up(key_cmd).perform()
                time.sleep(1.8)
                logger.info("본문 붙여넣기 완료 (Selenium)")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Selenium 붙여넣기 실패, pyautogui로 fallback: %s", exc)

        # Fallback: pyautogui 사용
        logger.info("본문 영역 못 찾음 - pyautogui로 붙여넣기")
        pyautogui.click(*self.BODY_POS)
        time.sleep(0.25)
        pyautogui.press("esc")
        time.sleep(0.05)
        pyautogui.press("enter")
        time.sleep(0.05)
        pyautogui.press("up")
        time.sleep(0.1)
        self._hotkey("ctrl", "v")
        time.sleep(1.8)

    def write_post_with_html_viewer(
        self, title: str, body_html: str, *, dry_run: bool = False
    ):
        try:
            # 1. HTML 뷰어로 이동하여 본문을 리치 포맷으로 변환
            self._copy_html_as_rich(body_html)

            # 2. 네이버 블로그로 이동
            driver = self.driver
            driver.get("https://blog.naver.com/GoBlogWrite.naver")
            time.sleep(3)

            # 3. 에디터 준비 및 팝업 제거 (추가)
            if not self.prepare_editor():
                raise RuntimeError("에디터 준비 실패: 팝업 제거 또는 제목 필드를 찾지 못했습니다.")

            # 4. 제목 입력
            self._write_title(title)

            # 5. 본문 붙여넣기
            self._paste_body_in_naver_blog()

            # 6. 발행 클릭 (테스트 모드인 경우 생략)
            if dry_run:
                logger.info("테스트 모드 - 네이버 발행 단계 생략")
            else:
                self.click_publish()

            self.random_sleep(1.2, 1.8)
            if dry_run:
                self.last_post_url = None
            else:
                self.last_post_url = self.driver.current_url
            return True

        except Exception as exc:
            logger.error("네이버 글 작성 실패: %s", exc)
            self._dump_debug_artifacts()
            return False

    def _extract_post_url(self) -> Optional[str]:
        driver = self.driver
        try:
            original_handle = driver.current_window_handle
        except Exception:  # noqa: BLE001
            original_handle = None

        def _inspect_window_handles() -> Optional[str]:
            handles = driver.window_handles
            for handle in reversed(handles):
                try:
                    driver.switch_to.window(handle)
                except Exception:  # noqa: BLE001
                    continue
                current = driver.current_url
                if self._is_valid_post_url(current):
                    return current
            return None

        try:
            # 1) 발행 완료 모달의 '글 보러가기' 버튼 클릭 시도
            view_button_selectors = [
                "button.se-published-view-button",
                "button.se_publish_view_button",
                "button.btn_view_post",
                "button.btn_gopost",
            ]
            for selector in view_button_selectors:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if not button.is_displayed():
                        continue
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        self.random_sleep(1.0, 1.8)
                    except Exception:  # noqa: BLE001
                        continue
                    view_url = _inspect_window_handles()
                    if view_url:
                        logger.info("발행 뷰 버튼을 통해 URL 추출: %s", view_url)
                        return view_url

            # 2) 모달의 링크 태그 직접 파싱
            link_selectors = [
                "a.se-published-view-link",
                "a.se_publish_view_link",
                "a.btn_view_post",
                "a.confirm_btn__WEaBq",
            ]
            for selector in link_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if not element.is_displayed():
                        continue
                    href = element.get_attribute("href")
                    if self._is_valid_post_url(href):
                        logger.info("네이버 발행 URL 추출 성공: %s", href)
                        return href

            # 3) 자바스크립트 상태에서 blogId/postNo 조합
            try:
                publish_meta = driver.execute_script(
                    """
                const publish = window.__PUBLISH_DATA__ ||
                                (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.publish) ||
                                null;
                if (!publish) return null;
                const blogId = publish.blogId || publish.blogNo || publish.blogIdNo;
                const postId = publish.postNo || publish.postId || publish.articleNo;
                if (!blogId || !postId) return null;
                return { blogId, postId };
                """
                )
            except Exception:  # noqa: BLE001
                publish_meta = None

            if publish_meta:
                blog_id = publish_meta.get("blogId") or self.blog_id
                post_id = publish_meta.get("postId")
                if blog_id and post_id:
                    posting_url = f"https://blog.naver.com/{blog_id}/{post_id}"
                    logger.info(
                        "window.__INITIAL_STATE__ 에서 발행 URL 구성: %s", posting_url
                    )
                    return posting_url

            # 4) 열린 창/탭을 순회하여 현재 URL 확인
            view_url = _inspect_window_handles()
            if view_url:
                logger.info("윈도우 핸들 순회 중 URL 추출: %s", view_url)
                return view_url

            # 5) URL 리디렉션 여부 확인 후 최종 fallback
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: ("blog.naver.com" in d.current_url)
                    and ("PostView" in d.current_url or "Redirect" not in d.current_url)
                )
            except TimeoutException:
                pass

            current_url = driver.current_url
            if self._is_valid_post_url(current_url):
                logger.info("현재 브라우저 URL을 발행 URL로 사용: %s", current_url)
                return current_url

            logger.warning("네이버 발행 URL을 찾지 못했습니다.")
            return None
        finally:
            if original_handle:
                try:
                    driver.switch_to.window(original_handle)
                except Exception:  # noqa: BLE001
                    pass

    def _is_valid_post_url(self, url: Optional[str]) -> bool:
        if not url:
            return False
        if "blog.naver.com" not in url:
            return False
        if "postWrite" in url:
            return False
        return True

    def _dump_debug_artifacts(self):
        try:
            log_dir = Path(__file__).resolve().parent / "logs"
            log_dir.mkdir(exist_ok=True)

            path_html = log_dir / "naver_page_source.html"
            with open(path_html, "w", encoding="utf-8") as file:
                file.write(self.driver.page_source)

            screenshot_path = log_dir / "naver_error.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info("디버깅용 HTML/스크린샷 저장 완료")
        except Exception as exc:  # noqa: BLE001
            logger.warning("디버깅 파일 저장 실패: %s", exc)

    def close(self):
        self.driver.quit()


def _build_driver_failure_result(
    *,
    error_code: str,
    user_message: str,
    exc: Exception,
) -> UploadResult:
    exception_type = exc.__class__.__name__
    logger.exception(
        "네이버 블로그 업로드 Selenium 예외 발생 (errorCode=%s, exception=%s)",
        error_code,
        exception_type,
    )
    metadata = {"errorCode": error_code, "exceptionType": exception_type}
    return UploadResult(
        platform="naver",
        success=False,
        message=user_message,
        metadata=metadata,
    )


def upload_to_naver_blog(
    content: Dict,
    *,
    naver_id: str,
    naver_pw: str,
    blog_url: str,
    headless: bool = False,
    wait_time: int = 10,
    dry_run: bool = False,
) -> UploadResult:
    """
    Standalone 호출용 래퍼
    """
    logger.info("네이버 블로그 업로드 시작")

    if not content or "title" not in content:
        message = "콘텐츠에 제목이 없습니다."
        logger.error(message)
        return UploadResult(platform="naver", success=False, message=message)

    title = content.get("title", "")
    body = content.get("body_html") or content.get("content", "")

    if not body:
        message = "콘텐츠에 본문이 없습니다."
        logger.error(message)
        return UploadResult(platform="naver", success=False, message=message)

    bot: NaverBlogAutomation | None = None
    try:
        bot = NaverBlogAutomation(
            naver_id=naver_id,
            naver_pw=naver_pw,
            blog_url=blog_url,
            headless=headless,
            wait_time=wait_time,
        )
        bot.login()
        success = bot.write_post_with_html_viewer(title, body, dry_run=dry_run)

        if success:
            logger.info("네이버 블로그 업로드 완료")
        else:
            logger.error("네이버 블로그 업로드 실패")

        return UploadResult(
            platform="naver",
            success=success,
            posting_url=bot.last_post_url,
        )

    except InvalidSessionIdException as exc:
        return _build_driver_failure_result(
            error_code="UPLOAD_DRIVER_LOST",
            user_message=_INVALID_SESSION_MESSAGE,
            exc=exc,
        )
    except WebDriverException as exc:
        return _build_driver_failure_result(
            error_code="UPLOAD_BROWSER_ERROR",
            user_message=_GENERIC_BROWSER_ERROR_MESSAGE,
            exc=exc,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("네이버 블로그 업로드 중 알 수 없는 오류 발생")
        metadata = {
            "errorCode": "UPLOAD_UNKNOWN_ERROR",
            "exceptionType": exc.__class__.__name__,
        }
        return UploadResult(
            platform="naver",
            success=False,
            message=_UNKNOWN_ERROR_MESSAGE,
            metadata=metadata,
        )

    finally:
        if bot:
            bot.close()
