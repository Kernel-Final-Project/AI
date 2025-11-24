# naver_blog_bot.py

import os
import time
import random
import platform
from typing import Dict
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from utils.load_env import get_env
from utils.logger import logger

# ================== 클래스 정의 ================== 
class NaverBlogAutomation:
    """
    네이버 블로그 자동 포스팅 클래스
    """

    def __init__(self):
        logger.info("네이버 블로그 자동화 시작")

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--lang=ko-KR")

        headless = get_env('HEADLESS', 'False').lower() == 'true'
        if headless:
            options.add_argument("--headless")
            logger.info("HEADLESS 모드로 실행 중")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

        wait_time = int(get_env('WAIT_TIME','10'))
        self.wait = WebDriverWait(self.driver, wait_time)
        self.actions = ActionChains(self.driver)
        self.is_mac = platform.system().lower() == 'darwin'

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

        naver_id = get_env("NAVER_ID")
        naver_pw = get_env('NAVER_PW')
        blog_url = get_env('NAVER_BLOG_URL')

        if not naver_id or not naver_pw or not blog_url:
            raise ValueError("NAVER_ID, NAVER_PW, NAVER_BLOG_URL이 설정되지 않았습니다.")

        # URL에서 blog_id 추출 (현재는 사용하지 않지만 향후 확장용)
        # 예: https://blog.naver.com/myblog123 -> myblog123
        try:
            parsed = urlparse(blog_url.rstrip('/'))
            self.blog_id = parsed.path.strip('/')
            logger.info(f"블로그 ID 추출: {self.blog_id}")
        except Exception as e:
            logger.warning(f"블로그 URL 파싱 실패 (무시): {e}")
            self.blog_id = None

        driver.get("https://nid.naver.com/nidlogin.login")
        self.random_sleep(2, 3)

        # 아이디 입력
        try:
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
            logger.info("아이디 입력 완료")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"아이디 입력 실패: {e}")
            raise

        # 비밀번호 입력
        try:
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
            logger.info("비밀번호 입력 완료")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"비밀번호 입력 실패: {e}")
            raise

        # 로그인 버튼 클릭
        try:
            login_btn = wait.until(EC.element_to_be_clickable((By.ID, "log.login")))
            login_btn.click()
            logger.info("로그인 버튼 클릭 완료")
            self.random_sleep(3, 4)
        except Exception as e:
            logger.error(f"로그인 버튼 클릭 실패: {e}")
            raise

        # 새 브라우저 등록 팝업 처리
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
                logger.info("새 브라우저 등록 팝업 닫기 완료")
                time.sleep(1)
        except Exception as e:
            logger.warning(f"새 브라우저 팝업 처리 중 예외 (무시): {e}")

        logger.info("네이버 로그인 완료")

    # ------------------------ 도움말 패널 닫기 ------------------------
    def close_help_panel(self):
        """
        네이버 새 에디터 도움말/가이드 패널 닫기
        """
        driver = self.driver
        logger.info("도움말 패널 닫기 시도...")

        # JS로 닫기
        try:
            driver.execute_script(
                """
            var btn = document.querySelector('.se-help-panel-close-button');
            if (btn) { btn.click(); return true; } return false;
            """
            )
            time.sleep(1)
        except Exception:
            pass

        # CSS 셀렉터로 닫기
        try:
            help_buttons = driver.find_elements(
                By.CSS_SELECTOR, ".se-help-panel-close-button"
            )
            for btn in help_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("도움말 패널 닫기 (CSS)")
                    time.sleep(1)
        except Exception:
            pass

        # XPath로 닫기
        try:
            xpath_buttons = driver.find_elements(
                By.XPATH, "//button[contains(@class, 'se-help-panel-close-button')]"
            )
            for btn in xpath_buttons:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("도움말 패널 닫기 (XPath)")
                    time.sleep(1)
        except Exception:
            pass

        # ESC 키로 닫기
        try:
            actions = ActionChains(driver)
            actions.send_keys(Keys.ESCAPE).perform()
            logger.info("ESC로 도움말 패널 닫기 시도")
            time.sleep(1)
        except Exception:
            pass

        logger.info("도움말 패널 닫기 시도 완료")

    # ------------------------ 글쓰기 페이지 준비 ------------------------
    def prepare_editor(self) -> bool:
        """
        - 네이버 글쓰기 페이지 이동 (GoBlogWrite)
        - mainFrame 전환
        - 도움말/팝업 닫기
        - 제목 필드 존재 여부 확인
        """
        driver = self.driver
        wait = self.wait

        logger.info("글쓰기 페이지 준비 시작")
        driver.get("https://blog.naver.com/GoBlogWrite.naver")
        time.sleep(3)

        # 페이지 로드 완료 대기
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.info("글쓰기 페이지 로드 완료")

        # mainFrame 전환
        try:
            driver.switch_to.default_content()
            main_frame = wait.until(
                EC.presence_of_element_located((By.ID, "mainFrame"))
            )
            driver.switch_to.frame(main_frame)
            logger.info("mainFrame iframe 전환 성공")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"mainFrame 전환 실패 (그래도 계속 진행): {e}")

        # 도움말 패널 닫기
        self.close_help_panel()

        # 기타 팝업 닫기
        try:
            # "새로 작성" 버튼
            continue_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), '새로 작성')]"
            )
            for btn in continue_buttons:
                if btn.is_displayed():
                    btn.click()
                    logger.info("새로 작성 버튼 클릭")
                    time.sleep(1)

            # "취소" 버튼
            cancel_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), '취소')]"
            )
            for btn in cancel_buttons:
                if btn.is_displayed():
                    btn.click()
                    logger.info("취소 버튼 클릭")
                    time.sleep(1)

            # 시작하기/닫기/close 클래스 등
            close_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(text(), '시작하기') or contains(text(), '닫기') "
                "or contains(@class, 'close') or contains(@class, 'cancel')]",
            )
            for btn in close_buttons:
                if btn.is_displayed():
                    btn.click()
                    logger.info("기타 팝업 버튼 클릭")
                    time.sleep(1)
        except Exception as e:
            logger.warning(f"팝업 처리 중 오류 (무시): {e}")

        # 제목 필드 존재 여부 확인
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
        except Exception as e:
            logger.error(f"에디터 준비 상태 확인 중 오류: {e}")
            return False

    # ------------------------ 발행 버튼 클릭 (2단계) ------------------------
    def click_publish(self):
        """
        1단계: 편집 화면 상단의 '발행' 버튼 클릭 (publish_btn__m9KHH)
        2단계: 발행 설정 레이어 내부의 최종 '발행' 버튼 클릭 (confirm_btn__WEaBq)
        """
        driver = self.driver
        wait = self.wait

        # 1단계: 상단 발행 버튼 클릭
        try:
            first_publish_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.publish_btn__m9KHH")
                )
            )
            driver.execute_script(
                "arguments[0].scrollIntoView(true);", first_publish_btn
            )
            time.sleep(0.3)
            first_publish_btn.click()
            logger.info("1단계 발행 버튼 클릭 완료 (레이어 오픈)")
        except Exception as e:
            logger.error(f"1단계 발행 버튼 클릭 실패: {e}")
            raise

        self.random_sleep(0.7, 1.2)

        # 2단계: 레이어 내부의 최종 발행 버튼 클릭
        try:
            final_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.confirm_btn__WEaBq")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", final_btn)
            time.sleep(0.3)
            final_btn.click()
            logger.info("2단계 최종 발행 버튼 클릭 완료")
        except Exception as e:
            logger.error(f"2단계 최종 발행 버튼 클릭 실패: {e}")
            raise

    # ------------------------ 실제 글 작성 로직 ------------------------
    def _write_into_editor(self, title: str, content: str) -> bool:
        driver = self.driver
        actions = self.actions

        # 1) 제목 입력
        try:
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
            logger.info(f"제목 입력: {title}")
            self.human_type_actions(title)
            logger.info("제목 입력 완료")
        except Exception as e:
            logger.error(f"제목 입력 중 오류: {e}")
            raise

        # 2) 본문 입력
        try:
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
                    if (
                        el.is_displayed()
                        and el.get_attribute("contenteditable") == "true"
                    ):
                        body_elem = el
                        break

            if not body_elem:
                raise Exception("본문 입력 필드를 찾을 수 없습니다.")

            body_elem.click()
            time.sleep(0.5)
            self.select_all_and_delete()

            logger.info("본문 입력 시작")
            lines = content.split("\n")
            for line in lines:
                self.human_type_actions(line)
                actions.send_keys("\n").perform()
                time.sleep(0.05)
            logger.info("본문 입력 완료")
        except Exception as e:
            logger.error(f"본문 입력 중 오류: {e}")
            raise

        # 3) 발행 처리 (임시저장 X, 진짜 발행 O)
        try:
            self.click_publish()
            logger.info("네이버 글 최종 발행 완료")
        except Exception as e:
            logger.error(f"발행 처리 중 오류: {e}")
            raise

        return True

    # ------------------------ 외부에서 쓰는 메인 메서드 ------------------------
    def write_post(self, title: str, content: str) -> bool:
        """메인 메서드: 제목/본문 입력 후 발행"""
        try:
            if not self.prepare_editor():
                raise Exception("글쓰기 에디터 준비 실패")

            if self._write_into_editor(title, content):
                logger.info("네이버 글 작성 및 발행 전체 프로세스 완료")
                return True
            return False
        except Exception as e:
            logger.error(f"네이버 글 작성 실패: {e}")
            # 디버깅용 파일 저장
            try:
                log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
                os.makedirs(log_dir, exist_ok=True)

                path_html = os.path.join(log_dir, "naver_page_source.html")
                with open(path_html, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                screenshot_path = os.path.join(log_dir, "naver_error.png")
                self.driver.save_screenshot(screenshot_path)
                logger.info("디버깅용 HTML/스크린샷 저장 완료")
            except Exception as e2:
                logger.warning(f"디버깅 파일 저장 실패: {e2}")
            return False

    def close(self):
        """브라우저 종료"""
        self.driver.quit()

  # ========== 프로젝트 인터페이스 래퍼 함수 ==========
def upload_to_naver_blog(content: Dict) -> bool:
    """
    프로젝트 스케줄러에서 호출하는 메인 함수
    
    Args:
        content: 업로드할 콘텐츠 딕셔너리
        {
            "title": "...",
            "body_html": "...",  # 또는 "content"
        }
        
    Returns:
        업로드 성공 여부
    """
    logger.info("네이버 블로그 업로드 시작")

    # 콘텐츠 검증
    if not content or 'title' not in content:
        logger.error("콘텐츠에 제목이 없습니다.")
        return False

    title = content.get('title', '')
    body = content.get('body_html') or content.get('content', '')

    if not body:
        logger.error("콘텐츠에 본문이 없습니다.")
        return False

    # 봇 인스턴스 생성 및 실행
    bot = None
    try:
        bot = NaverBlogAutomation()
        bot.login()
        success = bot.write_post(title, body)

        if success:
            logger.info("네이버 블로그 업로드 완료")
        else:
            logger.error("네이버 블로그 업로드 실패")

        return success

    except Exception as e:
        logger.error(f"네이버 블로그 업로드 중 오류: {e}")
        return False

    finally:
        if bot:
            bot.close()