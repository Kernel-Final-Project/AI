# src/tistory_blog_bot.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException

import time, os, random
from typing import Dict

from utils.load_env import get_env
from utils.logger import logger


class TistoryBlogAutomation:
    def __init__(self):
        logger.info("티스토리 블로그 자동화 시작")

        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--lang=ko-KR')

        headless = get_env('HEADLESS', 'False').lower() == 'true'
        if headless:
            options.add_argument('--headless')

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # webdriver 탐지 우회
        self.driver.execute_cdp_cmd(
            'Page.addScriptToEvaluateOnNewDocument',
            {'source': "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )

        wait_time = int(get_env('WAIT_TIME',10))
        self.wait = WebDriverWait(self.driver, wait_time)
        self.actions = ActionChains(self.driver)

        # 블로그 URL 설정
        blog_url = get_env('TISTORY_BLOG_URL','').rstrip('/')
        if not blog_url:
            raise ValueError("TISTOR_BLOG_URL 환경변수가 설정되지 않았습니다.")
        self.blog_write_url = blog_url + "/manage/newpost/"

    # ------------------------ Utility ------------------------
    def random_sleep(self, a=1, b=2):
        time.sleep(random.uniform(a, b))

    def human_type(self, el, text):
        for c in text:
            el.send_keys(c)
            time.sleep(random.uniform(0.03, 0.12))

    # ------------------------ 카카오 로그인 ------------------------
    def login(self):
        logger.info("티스토리(카카오) 로그인 시작")

        kakao_id = get_env('KAKAO_ID') or get_env('TISTORY_ID')
        kakao_pw = get_env('KAKAO_PASSWORD') or get_env('TISTORY_PW')

        if not kakao_id or not kakao_pw:
            raise ValueError("카카오 계정 정보가 존재하지 않습니다.")
        
        self.driver.get("https://www.tistory.com/auth/login")
        self.random_sleep(2, 3)

        # 1) 카카오 로그인 버튼 클릭
        kakao_btn = self.wait.until(
            EC.element_to_be_clickable((
                By.XPATH, "//*[contains(text(),'카카오계정으로')]"
            ))
        )
        kakao_btn.click()
        self.random_sleep(2, 3)

        # 2) 창 전환 (카카오가 새 창/팝업으로 뜰 수 있음)
        if len(self.driver.window_handles) > 1:
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.random_sleep(1, 2)

        # 3) 아이디 입력 필드 탐색 (모든 경우 대응)
        id_candidates = [
            "input#loginId--1",
            "input[name='loginId']",
            "input[id*='loginId']",
            "input[type='email']",
            "//input[contains(@placeholder, '카카오계정')]",
        ]

        id_input = None
        for sel in id_candidates:
            try:
                if sel.startswith("//"):
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, sel))
                    )
                else:
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                break
            except:
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

        # 4) 비밀번호 입력 필드 탐색
        pw_candidates = [
            "input#password--2",
            "input[name='password']",
            "input[type='password']",
            "//input[contains(@placeholder, '비밀번호')]",
        ]

        pw_input = None
        for sel in pw_candidates:
            try:
                if sel.startswith("//"):
                    pw_input = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, sel))
                    )
                else:
                    pw_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                break
            except:
                continue

        if pw_input is None:
            raise Exception("카카오 비밀번호 입력칸을 찾을 수 없습니다.")

        self.driver.execute_script("arguments[0].scrollIntoView(true);", pw_input)
        self.random_sleep(0.5, 1)
        pw_input.click()
        self.random_sleep(0.2, 0.4)
        pw_input.clear()
        self.human_type(pw_input, kakao_pw)

        # 5) 로그인 버튼 클릭
        login_btn_candidates = [
            "button[type='submit']",
            "//button[contains(text(), '로그인')]",
            "//button[contains(text(),'로그인') and @type='submit']"
        ]

        for sel in login_btn_candidates:
            try:
                if sel.startswith("//"):
                    btn = self.driver.find_element(By.XPATH, sel)
                else:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                break
            except:
                continue

        self.random_sleep(3, 5)


    # ------------------------ 글쓰기 UI 대기 ------------------------
    def wait_editor_loaded(self):
        """
        최신 Tistory NEW Editor에서 제목 입력칸 #post-title-inp 로딩될 때까지 기다림
        """
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#post-title-inp")
                )
            )
            self.random_sleep(1, 2)
        except TimeoutException:
            raise TimeoutException("티스토리 에디터의 제목 입력 칸(#post-title-inp)을 찾지 못했습니다.")

    # ------------------------ 제목 입력 ------------------------
    def enter_title(self, title: str):
        el = self.wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#post-title-inp"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", el)
        self.random_sleep(0.2, 0.4)

        el.click()
        self.random_sleep(0.2, 0.4)

        el.send_keys(Keys.CONTROL, 'a')
        el.send_keys(Keys.BACKSPACE)

        self.human_type(el, title)

    # ------------------------ 본문 입력 ------------------------
    def enter_content(self, content: str):
        # 1) TinyMCE iframe 찾기
        iframe = self.wait.until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.CSS_SELECTOR, "iframe#editor-tistory_ifr")
            )
        )

        # 2) iframe 내부의 body= 본문
        body = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "body#tinymce"))
        )

        self.driver.execute_script("arguments[0].scrollIntoView(true);", body)
        self.random_sleep(0.2, 0.4)

        body.click()
        self.random_sleep(0.2, 0.3)

        body.send_keys(Keys.CONTROL, 'a')
        body.send_keys(Keys.BACKSPACE)

        self.human_type(body, content)

        # 3) 다시 메인 문서로 복귀
        self.driver.switch_to.default_content()


    # ------------------------ 발행 버튼 클릭 ------------------------
    def click_publish(self):
        # 1) '완료' 버튼 클릭 → 발행 설정 창 열림
        complete_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-layer-btn"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", complete_btn)
        self.random_sleep(0.2, 0.4)
        complete_btn.click()
        self.random_sleep(1, 2)

        # 2) 발행 옵션에서 '공개(open20)' 선택
        try:
            open_public = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#open20"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", open_public)
            self.random_sleep(0.3, 0.5)
            open_public.click()
            self.random_sleep(0.3, 0.6)
        except Exception as e:
            logger.error("공개 라디오 버튼(#open20)을 찾을 수 없음")
            raise e

        # 3) 최종 발행 버튼 '공개 발행' 클릭
        publish_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#publish-btn"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", publish_btn)
        self.random_sleep(0.3, 0.5)
        publish_btn.click()

        self.random_sleep(3, 4)
        logger.info("티스토리 공개 발행 완료")

    # ------------------------ MAIN ------------------------
    def write_post(self, title: str, content: str):
        try:
            logger.info(f"티스토리 글쓰기 페이지 이동: {self.blog_write_url}")
            
            # 👉 1) 글쓰기 페이지 요청
            self.driver.get(self.blog_write_url)
            self.random_sleep(2, 3)

            # 👉 2) 페이지 로딩 중 뜨는 모든 alert 즉시 닫기
            try:
                alert = self.driver.switch_to.alert
                logger.info(f"[ALERT DETECTED] {alert.text}")
                alert.dismiss()  # '취소' = 새 글로 작성
                self.random_sleep(1, 1.5)
            except NoAlertPresentException:
                pass
            except UnexpectedAlertPresentException:
                try:
                    alert = self.driver.switch_to.alert
                    logger.info(f"[ALERT DETECTED 2] {alert.text}")
                    alert.dismiss()
                    self.random_sleep(1, 1.5)
                except:
                    pass

            # 👉 3) 혹시 alert가 늦게 뜨는 경우도 한 번 더 처리
            self.random_sleep(0.5, 1)
            try:
                alert = self.driver.switch_to.alert
                logger.info(f"[LATE ALERT] {alert.text}")
                alert.dismiss()
                self.random_sleep(1, 1.5)
            except:
                pass

            # 👉 4) 에디터 로딩 대기
            self.wait_editor_loaded()  # (#post-title-inp 보기)

            # 👉 5) 제목 입력
            self.enter_title(title)

            # 👉 6) 본문 입력
            self.enter_content(content)

            self.random_sleep(1, 2)

            # 👉 7) 발행
            self.click_publish()

            logger.info("티스토리 글 발행 완료")

        except Exception as e:
            # 디버깅용
            path_html = os.path.join(settings.LOG_DIR, 'tistory_page_source.html')
            with open(path_html, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)

            screenshot_path = os.path.join(settings.LOG_DIR, 'tistory_error.png')
            self.driver.save_screenshot(screenshot_path)

            logger.error(f"티스토리 글쓰기 중 에러 발생: {e}")
            raise

    def close(self):
        self.driver.quit()

    # ========== 프로젝트 인터페이스 래퍼 함수 ==========
def upload_to_tistory_blog(content: Dict) -> bool:
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
    logger.info("티스토리 블로그 업로드 시작")

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
        bot = TistoryBlogAutomation()
        bot.login()
        bot.write_post(title, body)

        logger.info("티스토리 블로그 업로드 완료")
        return True

    except Exception as e:
        logger.error(f"티스토리 블로그 업로드 중 오류: {e}")
        return False

    finally:
        if bot:
            bot.close()

