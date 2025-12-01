"""
Standalone Naver blog uploader (copied from auto_posting/naver_uploader.py).
"""
from __future__ import annotations

import platform
import random
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import build_chrome_driver
from .logger import logger
from .results import UploadResult


class NaverBlogAutomation:
    """
    네이버 블로그 자동 업로드 봇 (standalone 버전)
    """

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
            raise ValueError("NAVER_ID, NAVER_PW, NAVER_BLOG_URL이 설정되지 않았습니다.")

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
        logger.info("도움말 패널 닫기 시도...")

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

        logger.info("도움말 패널 닫기 시도 완료")

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
            main_frame = wait.until(EC.presence_of_element_located((By.ID, "mainFrame")))
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

        first_publish_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.publish_btn__m9KHH"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", first_publish_btn)
        time.sleep(0.3)
        first_publish_btn.click()
        self.random_sleep(0.7, 1.2)

        final_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.confirm_btn__WEaBq"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", final_btn)
        time.sleep(0.3)
        final_btn.click()

    # ------------------------ 실제 글 작성 로직 ------------------------
    def _write_into_editor(self, title: str, content: str) -> bool:
        driver = self.driver
        actions = self.actions

        title_selectors = [
            ".se-section-documentTitle",
            ".se-documentTitle-input",
            ".document_title",
            "input.se-ff-nanummyeongjo",
        ]

        title_elem = None
        for selector in title_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elems:
                if el.is_displayed():
                    title_elem = el
                    break
            if title_elem:
                break

        if not title_elem:
            xpath_elems = driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'title') or contains(@placeholder, '제목')]",
            )
            for el in xpath_elems:
                if el.is_displayed():
                    title_elem = el
                    break

        if not title_elem:
            raise Exception("제목 입력 필드를 찾을 수 없습니다.")

        title_elem.click()
        time.sleep(0.5)
        self.select_all_and_delete()
        self.human_type_actions(title)

        body_selectors = [
            ".se-section-text",
            ".se-text-paragraph",
            ".content_text",
            ".se-main-container",
        ]

        body_elem = None
        for selector in body_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elems:
                if el.is_displayed():
                    body_elem = el
                    break
            if body_elem:
                break

        if not body_elem:
            xpath_elems = driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'content') or "
                "contains(@class, 'text') or "
                "contains(@class, 'body')]",
            )
            for el in xpath_elems:
                if el.is_displayed() and el.get_attribute("contenteditable") == "true":
                    body_elem = el
                    break

        if not body_elem:
            raise Exception("본문 입력 필드를 찾을 수 없습니다.")

        body_elem.click()
        time.sleep(0.5)
        self.select_all_and_delete()

        lines = content.split("\n")
        for line in lines:
            self.human_type_actions(line)
            actions.send_keys("\n").perform()
            time.sleep(0.05)

        self.click_publish()

        # 발행 완료 후 잠시 대기하여 리디렉션/모달을 처리한다.
        self.random_sleep(1.0, 1.8)
        self.last_post_url = self._extract_post_url()
        return True

    def write_post(self, title: str, content: str) -> bool:
        try:
            if not self.prepare_editor():
                raise Exception("글쓰기 에디터 준비 실패")

            if self._write_into_editor(title, content):
                logger.info("네이버 글 작성 및 발행 전체 프로세스 완료")
                return True
            return False
        except Exception as exc:  # noqa: BLE001
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
                    logger.info("window.__INITIAL_STATE__ 에서 발행 URL 구성: %s", posting_url)
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


def upload_to_naver_blog(
    content: Dict,
    *,
    naver_id: str,
    naver_pw: str,
    blog_url: str,
    headless: bool = False,
    wait_time: int = 10,
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
        success = bot.write_post(title, body)

        if success:
            logger.info("네이버 블로그 업로드 완료")
        else:
            logger.error("네이버 블로그 업로드 실패")

        return UploadResult(
            platform="naver",
            success=success,
            posting_url=bot.last_post_url,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("네이버 블로그 업로드 중 오류: %s", exc)
        return UploadResult(platform="naver", success=False, message=str(exc))

    finally:
        if bot:
            bot.close()
