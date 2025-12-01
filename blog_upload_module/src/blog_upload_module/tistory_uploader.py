"""
Standalone Tistory uploader.
"""
from __future__ import annotations

import random
import re
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.common.exceptions import (
    NoAlertPresentException,
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import build_chrome_driver
from .logger import logger
from .results import UploadResult


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
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(),'카카오계정으로')]"))
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
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#post-title-inp")))
            self.random_sleep(1, 2)
        except TimeoutException as exc:
            raise TimeoutException(
                "티스토리 에디터의 제목 입력 칸(#post-title-inp)을 찾지 못했습니다."
            ) from exc

    # ------------------------ 제목 입력 ------------------------
    def enter_title(self, title: str):
        element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#post-title-inp")))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        self.random_sleep(0.2, 0.4)
        element.click()
        self.random_sleep(0.2, 0.4)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)
        self.human_type(element, title)

    # ------------------------ 본문 입력 ------------------------
    def enter_content(self, content: str):
        iframe = self.wait.until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe#editor-tistory_ifr"))
        )

        body = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "body#tinymce")))

        self.driver.execute_script("arguments[0].scrollIntoView(true);", body)
        self.random_sleep(0.2, 0.4)

        body.click()
        self.random_sleep(0.2, 0.3)

        body.send_keys(Keys.CONTROL, "a")
        body.send_keys(Keys.BACKSPACE)

        self.human_type(body, content)
        self.driver.switch_to.default_content()

    # ------------------------ 발행 버튼 클릭 ------------------------
    def click_publish(self):
        complete_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-layer-btn")))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", complete_btn)
        self.random_sleep(0.2, 0.4)
        complete_btn.click()
        self.random_sleep(1, 2)

        try:
            open_public = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#open20")))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", open_public)
            self.random_sleep(0.3, 0.5)
            open_public.click()
            self.random_sleep(0.3, 0.6)
        except Exception as exc:  # noqa: BLE001
            logger.error("공개 라디오 버튼(#open20)을 찾을 수 없음")
            raise exc

        publish_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-btn")))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", publish_btn)
        self.random_sleep(0.3, 0.5)
        publish_btn.click()

        self.random_sleep(3, 4)
        logger.info("티스토리 공개 발행 완료")

    # ------------------------ MAIN ------------------------
    def write_post(self, title: str, content: str) -> bool:
        try:
            logger.info("티스토리 글쓰기 페이지 이동: %s", self.blog_write_url)

            self.driver.get(self.blog_write_url)
            self.random_sleep(2, 3)

            self._dismiss_alerts()
            self.wait_editor_loaded()
            self.enter_title(title)
            self.enter_content(content)
            self.random_sleep(1, 2)
            self.click_publish()

            logger.info("티스토리 글 발행 완료")

            self.random_sleep(1, 2)
            self.last_post_url = self._extract_post_url()
            if self.last_post_url:
                logger.info("티스토리 발행 URL: %s", self.last_post_url)

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
                    href = element.get_attribute("href") or element.get_attribute("data-url")
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
                pattern = re.compile(rf"{re.escape(base_url.rstrip('/'))}/[0-9A-Za-z/_-]+")
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
                    lambda d: "tistory.com" in d.current_url and "manage" not in d.current_url
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
        if parsed.path.strip("/").lower() == "feed" or parsed.path.lower().endswith("/feed"):
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
            view_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn_view, button.link_post")
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


def upload_to_tistory_blog(
    content: Dict,
    *,
    blog_url: str,
    kakao_id: str,
    kakao_pw: str,
    headless: bool = False,
    wait_time: int = 10,
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
        success = bot.write_post(title, body)

        if success:
            logger.info("티스토리 블로그 업로드 완료")
        else:
            logger.error("티스토리 블로그 업로드 실패")

        return UploadResult(
            platform="tistory",
            success=success,
            posting_url=bot.last_post_url,
        )

    except Exception as exc:  # noqa: BLE001
        logger.error("티스토리 블로그 업로드 중 오류: %s", exc)
        return UploadResult(platform="tistory", success=False, message=str(exc))

    finally:
        if bot:
            bot.close()
