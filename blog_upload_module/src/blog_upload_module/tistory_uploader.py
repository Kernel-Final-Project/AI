"""
Standalone Tistory uploader.
"""

from __future__ import annotations

import platform
import random
import pyperclip
import re
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoAlertPresentException,
    NoSuchElementException,
    TimeoutException,
    UnexpectedAlertPresentException,
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
_UNKNOWN_ERROR_MESSAGE = "티스토리 블로그 업로드 중 알 수 없는 오류가 발생했습니다."


class TistoryBlogAutomation:
    def __init__(
        self,
        *,
        blog_url: str,
        kakao_id: str,
        kakao_pw: str,
        headless: bool = False,
        wait_time: int = 10,
    ) -> None:
        logger.info("티스토리 블로그 자동화 시작")

        self.driver: webdriver.Chrome = build_chrome_driver(headless=headless)
        self.headless = headless

        self.wait = WebDriverWait(self.driver, wait_time)
        self.actions = ActionChains(self.driver)

        blog_url = (blog_url or "").rstrip("/")
        if not blog_url:
            raise ValueError("티스토리 블로그 URL이 필요합니다.")
        self.blog_base_url = blog_url
        self.blog_write_url = blog_url + "/manage/newpost/"
        try:
            parsed = urlparse(blog_url if "://" in blog_url else f"https://{blog_url}")
            self.blog_host = parsed.netloc.lower()
        except Exception:  # noqa: BLE001
            self.blog_host = ""

        self.kakao_id = kakao_id
        self.kakao_pw = kakao_pw
        self.last_post_url: Optional[str] = None
        self.current_editor_mode: str = "basic"

    # ------------------------ Utility ------------------------
    def random_sleep(self, a=1, b=2):
        time.sleep(random.uniform(a, b))

    def human_type(self, element, text):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.12))

    # ------------------------ 카카오 로그인 ------------------------
    def login(self):
        logger.info("티스토리(카카오) 로그인 시작")

        kakao_id = self.kakao_id
        kakao_pw = self.kakao_pw

        self.driver.get("https://www.tistory.com/auth/login")
        self.random_sleep(2, 3)

        kakao_btn = self.wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(text(),'카카오계정으로')]")
            )
        )
        kakao_btn.click()
        self.random_sleep(2, 3)

        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.random_sleep(1, 2)

        id_candidates = [
            "input#loginId--1",
            "input[name='loginId']",
            "input[id*='loginId']",
            "input[type='email']",
            "//input[contains(@placeholder, '카카오계정')]",
        ]

        id_input = None
        for selector in id_candidates:
            try:
                if selector.startswith("//"):
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                break
            except Exception:  # noqa: BLE001
                continue

        if id_input is None:
            raise Exception("카카오 아이디 입력칸을 찾을 수 없습니다.")

        self.driver.execute_script("arguments[0].scrollIntoView(true);", id_input)
        self.random_sleep(0.5, 1)
        id_input.click()
        self.random_sleep(0.2, 0.4)
        id_input.clear()
        self.human_type(id_input, kakao_id)
        self.random_sleep(0.5, 1)

        pw_candidates = [
            "input#password--2",
            "input[name='password']",
            "input[type='password']",
            "//input[contains(@placeholder, '비밀번호')]",
        ]

        pw_input = None
        for selector in pw_candidates:
            try:
                if selector.startswith("//"):
                    pw_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    pw_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                break
            except Exception:  # noqa: BLE001
                continue

        if pw_input is None:
            raise Exception("카카오 비밀번호 입력칸을 찾을 수 없습니다.")

        self.driver.execute_script("arguments[0].scrollIntoView(true);", pw_input)
        self.random_sleep(0.5, 1)
        pw_input.click()
        self.random_sleep(0.2, 0.4)
        pw_input.clear()
        self.human_type(pw_input, kakao_pw)

        login_btn_candidates = [
            "button[type='submit']",
            "//button[contains(text(), '로그인')]",
            "//button[contains(text(),'로그인') and @type='submit']",
        ]

        for selector in login_btn_candidates:
            try:
                if selector.startswith("//"):
                    btn = self.driver.find_element(By.XPATH, selector)
                else:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                break
            except Exception:  # noqa: BLE001
                continue

        self.random_sleep(3, 5)

    # ------------------------ 글쓰기 UI 대기 ------------------------
    def wait_editor_loaded(self):
        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#post-title-inp"))
            )
            self.random_sleep(1, 2)
        except TimeoutException as exc:
            raise TimeoutException(
                "티스토리 에디터의 제목 입력 칸(#post-title-inp)을 찾지 못했습니다."
            ) from exc

    def _install_auto_confirm(self) -> bool:
        """
        Override window.alert/confirm in both main window and editor iframe.
        """
        script = """
        return (function() {
            const overrideWindow = (win) => {
                if (!win) return false;
                try {
                    if (win.__OCP_CONFIRM_OVERRIDE_DONE) {
                        return true;
                    }
                    const nativeConfirm = win.confirm;
                    const nativeAlert = win.alert;
                    if (typeof nativeConfirm !== 'function' && typeof nativeAlert !== 'function') {
                        win.__OCP_CONFIRM_OVERRIDE_DONE = true;
                        return false;
                    }
                    if (typeof nativeConfirm === 'function') {
                        win.__OCP_NATIVE_CONFIRM = nativeConfirm;
                        win.confirm = function(message) {
                            try {
                                win.__OCP_LAST_CONFIRM_MESSAGE = message || '';
                            } catch (ignore) {}
                            return true;
                        };
                    }
                    if (typeof nativeAlert === 'function') {
                        win.__OCP_NATIVE_ALERT = nativeAlert;
                        win.alert = function(message) {
                            try {
                                win.__OCP_LAST_CONFIRM_MESSAGE = message || '';
                            } catch (ignore2) {}
                            return true;
                        };
                    }
                    win.__OCP_CONFIRM_OVERRIDE_DONE = true;
                    return true;
                } catch (err) {
                    return false;
                }
            };
            const result = { main: overrideWindow(window), iframe: false };
            try {
                const iframe = document.querySelector("iframe#editor-tistory_ifr");
                if (iframe && iframe.contentWindow) {
                    result.iframe = overrideWindow(iframe.contentWindow);
                }
            } catch (ignore) {}
            return result;
        })();
        """
        try:
            result = self.driver.execute_script(script) or {}
            main_enabled = bool(result.get("main"))
            iframe_enabled = bool(result.get("iframe"))
            logger.info(
                "편집기 confirm 자동 수락 활성화(main=%s, iframe=%s)",
                main_enabled,
                iframe_enabled,
            )
            return main_enabled or iframe_enabled
        except Exception as exc:  # noqa: BLE001
            logger.warning("편집기 confirm 무력화 스크립트 주입 실패: %s", exc)
            return False

    def _is_captcha_present(self) -> bool:
        driver = self.driver
        keyword_xpaths = [
            "//*[contains(text(), '자동 등록 방지')]",
            "//*[contains(text(), '자동등록방지')]",
            "//*[contains(text(), '자동입력 방지')]",
            "//*[contains(text(), '자동입력방지')]",
            "//*[contains(text(), '캡차')]",
        ]
        selectors = [
            (By.CSS_SELECTOR, "iframe[src*='captcha']"),
            (By.CSS_SELECTOR, "[id*='captcha']"),
            (By.CSS_SELECTOR, "[class*='captcha']"),
            (By.CSS_SELECTOR, "input[name*='captcha']"),
        ]

        for xpath in keyword_xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
            except Exception:  # noqa: BLE001
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return True
                except Exception:  # noqa: BLE001
                    continue

        for by, selector in selectors:
            try:
                elements = driver.find_elements(by, selector)
            except Exception:  # noqa: BLE001
                continue
            for element in elements:
                try:
                    if element.is_displayed():
                        return True
                except Exception:  # noqa: BLE001
                    continue
        return False

    def _wait_for_captcha_resolution(
        self, max_wait: int = 600, check_interval: int = 3
    ):
        if not self._is_captcha_present():
            return
        logger.warning(
            "캡챠(자동 등록 방지) 감지됨 - 사용자가 직접 입력을 완료할 때까지 대기합니다."
        )
        deadline = time.time() + max(5, max_wait)
        while time.time() < deadline:
            if not self._is_captcha_present():
                logger.info("캡챠가 해제되었습니다. 작업을 재개합니다.")
                self.random_sleep(1, 1.5)
                return
            time.sleep(max(1, check_interval))
        raise TimeoutException("캡챠가 해소되지 않아 작업을 중단합니다.")

    def switch_editor_mode(self, mode: str = "html"):
        """
        Open the mode dropdown (기본/마크다운/HTML) and switch to the requested mode.
        """
        self._install_auto_confirm()
        mode_map = {
            "basic": "#editor-mode-kakao",
            "kakao": "#editor-mode-kakao",
            "markdown": "#editor-mode-markdown",
            "md": "#editor-mode-markdown",
            "html": "#editor-mode-html",
        }
        requested = (mode or "").lower().strip()
        target_selector = mode_map.get(requested)
        if not target_selector:
            logger.warning("지원하지 않는 편집 모드입니다: %s", mode)
            return

        try:
            toggle_btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#editor-mode-layer-btn-open")
                )
            )
        except TimeoutException:
            logger.warning("편집 모드 전환 버튼을 찾을 수 없습니다.")
            return

        self._install_auto_confirm()
        self.driver.execute_script("arguments[0].scrollIntoView(true);", toggle_btn)
        self.random_sleep(0.2, 0.4)
        toggle_btn.click()
        self.random_sleep(0.2, 0.4)

        try:
            mode_option = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, target_selector))
            )
        except TimeoutException:
            logger.warning("편집 모드 옵션(%s)을 찾지 못했습니다.", target_selector)
            return

        try:
            mode_option.click()
        except UnexpectedAlertPresentException:
            logger.debug("모드 옵션 클릭 중 알림 발생, 알림 처리 시도")
        finally:
            self.random_sleep(0.3, 0.5)
            self._handle_mode_change_alert(timeout=5)

        # 드롭다운이 닫힐 시간을 조금 준다.
        try:
            self.wait.until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "div.mce-menu.mce-in")
                )
            )
        except TimeoutException:
            logger.debug("편집 모드 드롭다운 닫힘을 명확히 확인하지 못했습니다.")
        except UnexpectedAlertPresentException:
            logger.debug("드롭다운 닫힘 대기 중 알림 발생, 처리 시도")
            self._handle_mode_change_alert(timeout=5)

        self.current_editor_mode = requested
        if requested == "html":
            # HTML 모드는 DOM이 실제로 전환되지 않으면 이후 단계가 모두 실패하므로 즉시 검증한다.
            try:
                self._wait_html_editor_ready()
            except TimeoutException as exc:  # noqa: BLE001
                raise RuntimeError("HTML 편집 모드 전환에 실패했습니다.") from exc

    def _is_html_mode(self) -> bool:
        return getattr(self, "current_editor_mode", "").lower() == "html"

    def _has_html_editor_dom(self) -> bool:
        """
        Check both the main document and potential editor iframe for HTML-mode widgets.
        """
        script = """
        const inspect = (root) => {
            if (!root) return false;
            try {
                const cm = root.querySelector('.ReactCodemirror .CodeMirror');
                if (cm && cm.CodeMirror) {
                    const wrapper = cm.CodeMirror.getWrapperElement &&
                                    cm.CodeMirror.getWrapperElement();
                    if (wrapper && wrapper.offsetHeight > 0) {
                        return true;
                    }
                }
                const textarea = root.querySelector(
                    "textarea#editor-mode-html-textarea, textarea[data-mode='html'], textarea[id*='editor-mode'][id*='html']"
                );
                if (textarea && textarea.offsetParent !== null && textarea.offsetHeight > 0) {
                    return true;
                }
            } catch (ignore) {}
            return false;
        };
        if (inspect(document)) {
            return true;
        }
        const iframe = document.querySelector('iframe#editor-tistory_ifr');
        if (iframe && iframe.contentDocument) {
            if (inspect(iframe.contentDocument)) {
                return true;
            }
        }
        return false;
        """
        try:
            return bool(self.driver.execute_script(script))
        except Exception:  # noqa: BLE001
            return False

    def _handle_mode_change_alert(self, timeout: float = 3.0) -> bool:
        """
        티스토리 모드 변경 시 표시되는 확인 알림(작성 모드를 변경하시겠습니까?) 처리.
        """
        try:
            alert = WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
        except TimeoutException:
            return self._accept_mode_change_modal()

        text = ""
        try:
            text = alert.text or ""
        except Exception:  # noqa: BLE001
            text = ""

        logger.info("편집 모드 변경 알림 감지: %s", text.strip())
        try:
            alert.accept()
            self.random_sleep(0.5, 0.8)
        except Exception:  # noqa: BLE001
            try:
                alert.dismiss()
                self.random_sleep(0.3, 0.5)
            except Exception:  # noqa: BLE001
                pass
        return True

    def _accept_mode_change_modal(self) -> bool:
        """
        일부 환경에서 브라우저 alert 대신 DOM 모달을 띄울 수 있으므로 버튼을 직접 클릭한다.
        """
        selectors = [
            (By.CSS_SELECTOR, "div.mce-window button.mce-primary"),
            (By.CSS_SELECTOR, "div[role='dialog'] button[data-mce-focus]"),
            (By.XPATH, "//button[contains(text(), '확인')]"),
            (By.XPATH, "//span[contains(text(), '확인')]/parent::button"),
        ]
        for by, selector in selectors:
            try:
                element = self.driver.find_element(by, selector)
            except Exception:  # noqa: BLE001
                continue
            if not element.is_displayed():
                continue
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", element
                )
                self.random_sleep(0.2, 0.4)
                element.click()
                self.random_sleep(0.4, 0.6)
                logger.info("편집 모드 변경 모달 버튼 클릭으로 확인 처리")
                return True
            except Exception:  # noqa: BLE001
                continue
        return False

    # ------------------------ 제목 입력 ------------------------
    def enter_title(self, title: str):
        self._handle_mode_change_alert()
        element = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#post-title-inp"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        self.random_sleep(0.2, 0.4)
        element.click()
        self.random_sleep(0.2, 0.4)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        self.human_type(element, title)

    # ------------------------ HTML 본문 입력 ------------------------
    def paste_content_like_human(self, content: str, timeout: int = 15):
        driver = self.driver
        wait = WebDriverWait(driver, timeout)

        cm = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".CodeMirror"))
        )

        line = cm.find_element(By.CSS_SELECTOR, ".CodeMirror-line")

        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", line)

        ActionChains(driver).move_to_element_with_offset(line, 5, 5).click().perform()

        time.sleep(0.3)

        # 클립보드에 복사 및 검증
        pyperclip.copy(content)
        time.sleep(1.5)  # Mac 클립보드 동기화를 위해 대기 시간 증가

        # 클립보드 복사 성공 여부 확인
        clipboard_content = pyperclip.paste()
        if clipboard_content != content:
            logger.warning("클립보드 복사 실패 감지, 재시도 중...")
            time.sleep(1.0)
            pyperclip.copy(content)
            time.sleep(1.5)
            clipboard_content = pyperclip.paste()
            if clipboard_content != content:
                logger.error("클립보드 복사 2차 재시도 실패")
                return False
            logger.info("클립보드 복사 재시도 성공")
        else:
            logger.info("클립보드 복사 성공 확인")

        # Mac에서는 Command 키, 그 외에는 Control 키 사용
        is_mac = platform.system() == "Darwin"
        if is_mac:
            logger.info("Mac OS 감지 - Command+V 사용")
            ActionChains(driver).key_down(Keys.COMMAND).send_keys("v").key_up(
                Keys.COMMAND
            ).perform()
        else:
            logger.info("Windows/Linux - Ctrl+V 사용")
            ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(
                Keys.CONTROL
            ).perform()

        time.sleep(max(1.0, min(3, len(content) / 5000)))  # 최소 1초 대기
        return True

    def enter_content(self, content: str):
        """
        HTML 모드 본문 입력
        - 에디터 준비 확인
        - 실제 입력 (human_like)
        - 입력 적용 확인
        """
        logger.info("HTML 모드 본문 입력 시도!")

        self._handle_mode_change_alert()
        try:
            self._wait_html_editor_ready()
        except RuntimeError:
            self._dump_debug_artifacts()
            raise RuntimeError("HTML 에디터 준비 실패")

        if not self.paste_content_like_human(content):
            self._dump_debug_artifacts()
            raise RuntimeError("HTML 본문 입력 실패: CodeMirror/textarea 접근 불가")

        if not self._wait_html_content_applied(content, timeout=15):
            self._dump_debug_artifacts()
            raise RuntimeError("HTML 본문 검증 실패: 내용 불일치")

        logger.info("HTML 모드 본문 입력 완료 !!")

    def _wait_html_editor_ready(self, timeout: int = 15):
        """
        HTML 모드 에디터가 실제 입력 가능한 상태가 될 때까지 대기
        - 메인 DOM CodeMirror
        - 메인 DOM textarea
        - iframe 내 CodeMirror / textarea
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script(
                    """
                    function readyCM(cmContainer) { return cmContainer && cmContainer.CodeMirror; }
                    function readyTA(ta) { return ta && ta.offsetParent !== null; }

                    let cm = document.querySelector('.ReactCodemirror .CodeMirror');
                    if (readyCM(cm)) return true;

                    let ta = document.querySelector('textarea#editor-mode-html-textarea');
                    if (readyTA(ta)) return true;

                    const iframe = document.querySelector('iframe#editor-tistory_ifr');
                    if (iframe && iframe.contentDocument) {
                        const doc = iframe.contentDocument;
                        cm = doc.querySelector('.ReactCodemirror .CodeMirror');
                        if (readyCM(cm)) return true;
                        ta = doc.querySelector('textarea');
                        if (readyTA(ta)) return true;
                    }
                    return false;
                    """
                )
            )
            return True
        except TimeoutException:
            self._dump_debug_artifacts()
            raise RuntimeError("HTML 에디터 준비 실패: CodeMirror나 textarea 접근 불가")

    def _wait_html_content_applied(self, content: str, timeout=15) -> bool:
        """입력한 HTML이 실제 CodeMirror나 textarea에 반영됐는지 확인"""
        wait = WebDriverWait(self.driver, timeout)
        normalized_len = max(1, int(len(content.strip().replace(" ", "")) * 0.9))

        def _applied(driver):
            try:
                return driver.execute_script(
                    """
                    const minLen = arguments[0];

                    function checkCM(cmContainer) {
                        const val = cmContainer.CodeMirror.getValue() || '';
                        return val.replace(/\s+/g,'').length >= minLen;
                    }

                    function checkTA(ta) {
                        const val = ta.value || '';
                        return val.replace(/\s+/g,'').length >= minLen;
                    }

                    // 메인 CodeMirror
                    let cm = document.querySelector('.ReactCodemirror .CodeMirror');
                    if (cm && cm.CodeMirror && checkCM(cm)) return true;

                    // 메인 textarea
                    let ta = document.querySelector('textarea#editor-mode-html-textarea');
                    if (ta && ta.offsetParent !== null && checkTA(ta)) return true;

                    // iframe CodeMirror / textarea
                    const iframe = document.querySelector('iframe#editor-tistory_ifr');
                    if (iframe && iframe.contentDocument) {
                        const doc = iframe.contentDocument;
                        cm = doc.querySelector('.ReactCodemirror .CodeMirror');
                        if (cm && cm.CodeMirror && checkCM(cm)) return true;

                        ta = doc.querySelector('textarea');
                        if (ta && ta.offsetParent !== null && checkTA(ta)) return true;
                    }

                    return false;
                    """,
                    normalized_len,
                )
            except Exception:
                return False

        try:
            wait.until(_applied)
            return True
        except TimeoutException:
            logger.warning("HTML 본문이 기대 길이만큼 적용되지 않았습니다.")
            return False

    # ------------------------ 발행 버튼 클릭 ------------------------
    def click_publish(self):
        self._handle_mode_change_alert()
        self._wait_for_captcha_resolution()
        complete_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-layer-btn"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", complete_btn)
        self.random_sleep(0.2, 0.4)
        complete_btn.click()
        self.random_sleep(1, 2)
        self._wait_for_captcha_resolution()

        try:
            open_public = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#open20"))
            )
            self.driver.execute_script(
                "arguments[0].scrollIntoView(true);", open_public
            )
            self.random_sleep(0.3, 0.5)
            open_public.click()
            self.random_sleep(0.3, 0.6)
            self._wait_for_captcha_resolution()
        except Exception as exc:  # noqa: BLE001
            logger.error("공개 라디오 버튼(#open20)을 찾을 수 없음")
            raise exc

        publish_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-btn"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", publish_btn)
        self.random_sleep(0.3, 0.5)
        publish_btn.click()
        self._wait_for_captcha_resolution()

        self.random_sleep(3, 4)
        logger.info("티스토리 공개 발행 완료")

    # ------------------------ MAIN ------------------------
    def write_post(self, title: str, content: str, *, dry_run: bool = False) -> bool:
        try:
            logger.info("티스토리 글쓰기 페이지 이동: %s", self.blog_write_url)

            self.driver.get(self.blog_write_url)
            self.random_sleep(2, 3)

            self._dismiss_alerts()
            self._wait_for_captcha_resolution()
            self._install_auto_confirm()
            self.wait_editor_loaded()
            self.switch_editor_mode("html")
            self.enter_title(title)
            self.enter_content(content)
            self.random_sleep(1, 2)

            if dry_run:
                logger.info("테스트 모드 - 티스토리 발행 단계 생략")
            else:
                self.click_publish()
                logger.info("티스토리 글 발행 완료")
                self.random_sleep(1, 2)
                self.last_post_url = self._extract_post_url()
                if self.last_post_url:
                    logger.info("티스토리 발행 URL: %s", self.last_post_url)
            if dry_run:
                self.last_post_url = None

            return True

        except Exception as exc:  # noqa: BLE001
            self._dump_debug_artifacts()
            logger.error("티스토리 글쓰기 중 에러 발생: %s", exc)
            return False

    def _extract_post_url(self) -> Optional[str]:
        driver = self.driver
        base_url = getattr(self, "blog_base_url", "")
        try:
            original_handle = driver.current_window_handle
        except Exception:  # noqa: BLE001
            original_handle = None

        def inspect_handles() -> Optional[str]:
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                except Exception:  # noqa: BLE001
                    continue
                current = driver.current_url
                if self._is_valid_post_url(current):
                    return current
            return None

        try:
            # 1) 발행 완료 모달의 버튼 클릭
            view_button_selectors = [
                (By.CSS_SELECTOR, "button.link_post"),
                (By.CSS_SELECTOR, "button.view_post"),
                (By.CSS_SELECTOR, "button.btn_view"),
                (By.CSS_SELECTOR, "button#linkView"),
                (By.XPATH, "//button[contains(text(), '글 보러가기')]"),
            ]
            for by, selector in view_button_selectors:
                try:
                    elements = driver.find_elements(by, selector)
                except Exception:  # noqa: BLE001
                    continue
                for element in elements:
                    if not element.is_displayed():
                        continue
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        self.random_sleep(0.8, 1.5)
                    except Exception:  # noqa: BLE001
                        continue
                    url = inspect_handles()
                    if url:
                        logger.info("티스토리 발행 버튼 클릭으로 URL 확보: %s", url)
                        return url

            # 2) 링크 태그 파싱
            selectors = [
                (By.CSS_SELECTOR, "a.link_post"),
                (By.CSS_SELECTOR, "a.view_post"),
                (By.CSS_SELECTOR, "a.btn_view"),
                (By.CSS_SELECTOR, "a#linkView"),
                (By.XPATH, "//a[contains(text(), '글 보러가기')]"),
                (By.XPATH, "//a[contains(text(), '게시글 보기')]"),
            ]
            for by, selector in selectors:
                try:
                    elements = driver.find_elements(by, selector)
                except Exception:  # noqa: BLE001
                    continue
                for element in elements:
                    if not element.is_displayed():
                        continue
                    href = element.get_attribute("href") or element.get_attribute(
                        "data-url"
                    )
                    href = self._normalize_post_url(href)
                    if self._is_valid_post_url(href):
                        return href

            # 3) data-* 속성에서 후보 추출
            try:
                data_urls = driver.execute_script(
                    """
                const nodes = Array.from(document.querySelectorAll('[data-url],[data-link],[data-href],[data-view-url]'));
                return nodes
                  .map(el => el.dataset.url || el.dataset.link || el.dataset.href ||
                             el.dataset.viewUrl || el.getAttribute('data-url') ||
                             el.getAttribute('data-link') || el.getAttribute('data-href') ||
                             el.getAttribute('data-view-url'))
                  .filter(Boolean);
                """
                )
            except Exception:  # noqa: BLE001
                data_urls = []
            for href in data_urls:
                href = self._normalize_post_url(href)
                if self._is_valid_post_url(href):
                    return href

            # 4) window.__NUXT__ 등 JS 상태에서 조합
            try:
                publish_meta = driver.execute_script(
                    """
                const nuxt = (window.__NUXT__ && (window.__NUXT__.state || window.__NUXT__.data && window.__NUXT__.data[0])) || {};
                const entry = nuxt.entry || nuxt.post || nuxt.article || null;
                const blog = nuxt.blog || nuxt.blogInfo || {};
                const postUrl = entry && (entry.url || entry.postUrl || entry.permalink);
                const slug = entry && (entry.slug || entry.alias);
                const postId = entry && (entry.id || entry.postId || entry.entryId);
                const blogUrl = blog.url || blog.blogUrl || (window.__BLOG__ && window.__BLOG__.url) || null;
                return { postUrl, slug, postId, blogUrl };
                """
                )
            except Exception:  # noqa: BLE001
                publish_meta = None

            if publish_meta:
                candidates = []
                if publish_meta.get("postUrl"):
                    candidates.append(publish_meta["postUrl"])
                blog_url_state = publish_meta.get("blogUrl") or base_url
                slug = publish_meta.get("slug")
                post_id = publish_meta.get("postId")
                if blog_url_state and post_id:
                    candidates.append(f"{blog_url_state.rstrip('/')}/{post_id}")
                if blog_url_state and slug:
                    candidates.append(f"{blog_url_state.rstrip('/')}/{slug}")
                for href in candidates:
                    href = self._normalize_post_url(href)
                    if self._is_valid_post_url(href):
                        return href

            # 5) 페이지 내 모든 앵커 검색
            try:
                anchor_urls = driver.execute_script(
                    """
                return Array.from(document.querySelectorAll('a'))
                  .map(a => a.href || a.getAttribute('href'))
                  .filter(Boolean);
                """
                )
            except Exception:  # noqa: BLE001
                anchor_urls = []
            for href in anchor_urls:
                href = self._normalize_post_url(href)
                if self._is_valid_post_url(href):
                    return href

            # 6) HTML에서 정규식 추출
            if base_url:
                try:
                    html = driver.page_source
                except Exception:  # noqa: BLE001
                    html = ""
                pattern = re.compile(
                    rf"{re.escape(base_url.rstrip('/'))}/[0-9A-Za-z/_-]+"
                )
                for match in pattern.findall(html):
                    if self._is_valid_post_url(match):
                        return match

            # 7) 관리 목록 페이지에서 첫 글 역추적
            if "manage" in (driver.current_url or ""):
                manage_url = self._extract_from_manage_page()
                if manage_url:
                    return manage_url

            url = inspect_handles()
            if url:
                return url

            try:
                WebDriverWait(driver, 5).until(
                    lambda d: "tistory.com" in d.current_url
                    and "manage" not in d.current_url
                )
            except TimeoutException:
                pass

            current = driver.current_url
            if self._is_valid_post_url(current):
                return current

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
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if self.blog_host and host != self.blog_host.lower():
            return False
        if "tistory.com" not in host and self.blog_host.endswith("tistory.com"):
            return False
        if "manage" in url:
            return False
        if url.startswith("javascript"):
            return False
        if not parsed.path or parsed.path.strip("/") == "":
            return False
        if parsed.path.strip("/").lower() == "feed" or parsed.path.lower().endswith(
            "/feed"
        ):
            return False
        return True

    def _extract_from_manage_page(self) -> Optional[str]:
        driver = self.driver
        selectors = [
            "table.post-list tbody tr:first-child a.link_post",
            "table.post-list tbody tr:first-child a.btn_view",
            "table.post-list tbody tr:first-child a[href*='tistory.com']",
            "#content .post-list a.link_post",
            "a.manage_open_view",
            ".article-content a.link-article",
            ".article-content a[data-tiara-click_url]",
        ]
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
            except Exception:  # noqa: BLE001
                continue
            if not element.is_displayed():
                continue
            href = (
                element.get_attribute("href")
                or element.get_attribute("data-url")
                or element.get_attribute("data-tiara-click_url")
                or element.get_attribute("data-tiara-plink")
            )
            href = self._normalize_post_url(href)
            if self._is_valid_post_url(href):
                logger.info("목록 페이지에서 최신 글 URL 추출: %s", href)
                return href

        try:
            dataset_url = driver.execute_script(
                """
            const nodes = Array.from(document.querySelectorAll('[data-entry-url],[data-url],[data-link],[data-tiara-click_url],[data-tiara-plink]'));
            for (const node of nodes) {
                const href = node.dataset.entryUrl ||
                             node.dataset.url ||
                             node.dataset.link ||
                             node.dataset.tiaraClickUrl ||
                             node.getAttribute('data-tiara-click_url') ||
                             node.getAttribute('data-tiara-plink') ||
                             node.getAttribute('data-url');
                if (href) return href;
            }
            return null;
            """
            )
        except Exception:  # noqa: BLE001
            dataset_url = None

        dataset_url = self._normalize_post_url(dataset_url)
        if self._is_valid_post_url(dataset_url):
            logger.info("목록 행 data-* 에서 URL 추출: %s", dataset_url)
            return dataset_url

        try:
            view_buttons = driver.find_elements(
                By.CSS_SELECTOR, "button.btn_view, button.link_post"
            )
        except Exception:  # noqa: BLE001
            view_buttons = []
        for button in view_buttons:
            if not button.is_displayed():
                continue
            try:
                driver.execute_script("arguments[0].click();", button)
                self.random_sleep(0.5, 1.0)
                current = self._normalize_post_url(driver.current_url)
                if self._is_valid_post_url(current):
                    logger.info("목록 페이지 버튼 클릭으로 URL 추출: %s", current)
                    return current
                driver.back()
                self.random_sleep(0.5, 1.0)
            except Exception:  # noqa: BLE001
                continue

        return None

    def _normalize_post_url(self, href: Optional[str]) -> Optional[str]:
        if not href:
            return None
        href = href.strip()
        if not href:
            return None
        if href.startswith("//"):
            href = "https:" + href
        base = (self.blog_base_url or "").rstrip("/") + "/"
        if href.startswith("/"):
            href = urljoin(base, href)
        if href.startswith("http"):
            # collapse repeated slashes after scheme
            scheme, rest = href.split("://", 1)
            rest = re.sub(r"/{2,}", "/", rest)
            href = f"{scheme}://{rest}"
        return href

    def _dismiss_alerts(self):
        try:
            alert = self.driver.switch_to.alert
            logger.info("[ALERT DETECTED] %s", alert.text)
            alert.dismiss()
            self.random_sleep(1, 1.5)
        except NoAlertPresentException:
            pass
        except UnexpectedAlertPresentException:
            try:
                alert = self.driver.switch_to.alert
                logger.info("[ALERT DETECTED 2] %s", alert.text)
                alert.dismiss()
                self.random_sleep(1, 1.5)
            except Exception:  # noqa: BLE001
                pass

        self.random_sleep(0.5, 1)
        try:
            alert = self.driver.switch_to.alert
            logger.info("[LATE ALERT] %s", alert.text)
            alert.dismiss()
            self.random_sleep(1, 1.5)
        except Exception:  # noqa: BLE001
            pass

    def _dump_debug_artifacts(self):
        try:
            log_dir = Path(__file__).resolve().parent / "logs"
            log_dir.mkdir(exist_ok=True)

            path_html = log_dir / "tistory_page_source.html"
            with open(path_html, "w", encoding="utf-8") as file:
                file.write(self.driver.page_source)

            screenshot_path = log_dir / "tistory_error.png"
            self.driver.save_screenshot(screenshot_path)
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
        "티스토리 블로그 업로드 Selenium 예외 발생 (errorCode=%s, exception=%s)",
        error_code,
        exception_type,
    )
    metadata = {"errorCode": error_code, "exceptionType": exception_type}
    return UploadResult(
        platform="tistory",
        success=False,
        message=user_message,
        metadata=metadata,
    )


def upload_to_tistory_blog(
    content: Dict,
    *,
    blog_url: str,
    kakao_id: str,
    kakao_pw: str,
    headless: bool = False,
    wait_time: int = 10,
    dry_run: bool = False,
) -> UploadResult:
    """
    Standalone 호출용 래퍼
    """
    logger.info("티스토리 블로그 업로드 시작")

    if not content or "title" not in content:
        message = "콘텐츠에 제목이 없습니다."
        logger.error(message)
        return UploadResult(platform="tistory", success=False, message=message)

    title = content.get("title", "")
    body = content.get("body_html") or content.get("content", "")

    if not body:
        message = "콘텐츠에 본문이 없습니다."
        logger.error(message)
        return UploadResult(platform="tistory", success=False, message=message)

    bot: TistoryBlogAutomation | None = None
    try:
        bot = TistoryBlogAutomation(
            blog_url=blog_url,
            kakao_id=kakao_id,
            kakao_pw=kakao_pw,
            headless=headless,
            wait_time=wait_time,
        )
        bot.login()
        success = bot.write_post(title, body, dry_run=dry_run)

        if success:
            logger.info("티스토리 블로그 업로드 완료")
        else:
            logger.error("티스토리 블로그 업로드 실패")

        return UploadResult(
            platform="tistory",
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
        logger.exception("티스토리 블로그 업로드 중 알 수 없는 오류 발생")
        metadata = {
            "errorCode": "UPLOAD_UNKNOWN_ERROR",
            "exceptionType": exc.__class__.__name__,
        }
        return UploadResult(
            platform="tistory",
            success=False,
            message=_UNKNOWN_ERROR_MESSAGE,
            metadata=metadata,
        )

    finally:
        if bot:
            bot.close()
