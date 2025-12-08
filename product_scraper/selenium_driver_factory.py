
import random
import time
import os
import pickle
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc


class SeleniumDriverFactory:
    """
    Selenium + undetected-chromedriver 기반 스텔스 드라이버 팩토리
    쿠팡 봇 탐지 우회 최적화
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    ]

    def __init__(self, headless: bool = False, user_data_dir: str = None):
        self.headless = headless
        self.user_data_dir = user_data_dir or ".selenium_data"
        self.driver: Optional[webdriver.Chrome] = None

    def create_driver(self) -> webdriver.Chrome:
        """스텔스 설정이 적용된 Chrome 드라이버 생성"""
        # Headless 모드 상태 로깅
        mode = "Headless (숨김)" if self.headless else "Headed (브라우저 창 보임)"
        print(f"🌐 브라우저 모드: {mode}")

        # Chrome 옵션 설정 (일반 ChromeOptions 사용 - keywordCrawler 방식)
        options = webdriver.ChromeOptions()

        # 기본 옵션
        if not self.headless:
            options.add_argument("--start-maximized")

        # 스텔스 옵션 (봇 탐지 우회)
        options.add_argument('--disable-blink-features=AutomationControlled')
        #options.add_experimental_option("excludeSwitches", ["enable-automation"])
        #options.add_experimental_option('useAutomationExtension', False)

        # User-Agent 설정
        user_agent = random.choice(self.USER_AGENTS)
        options.add_argument(f'user-agent={user_agent}')

        # 한국어 설정
        options.add_argument('--lang=ko-KR')

        # Headless 모드
        if self.headless:
            options.add_argument("--headless=new")

        # undetected-chromedriver로 생성
        print("🚀 undetected-chromedriver로 Chrome 시작...")
        self.driver = uc.Chrome(options=options, use_subprocess=True)

        # JavaScript로 추가 스텔스 스크립트 주입
        self._inject_stealth_scripts()

        # 쿠키 로드
        self._load_cookies()

        return self.driver

    def _inject_stealth_scripts(self):
        """JavaScript로 추가 스텔스 스크립트 주입"""
        if not self.driver:
            return

        stealth_script = """
            // navigator.webdriver 제거
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Chrome 객체 모킹
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // 플러그인 모킹
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 언어 설정
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en']
            });
        """

        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': stealth_script
        })

    def _load_cookies(self):
        """저장된 쿠키 로드"""
        if not self.driver or not self.user_data_dir:
            return

        cookie_file = os.path.join(self.user_data_dir, 'cookies.pkl')
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        self.driver.add_cookie(cookie)
                print(f"💾 저장된 쿠키 로드: {cookie_file}")
            except Exception as e:
                print(f"쿠키 로드 실패: {e}")

    def save_cookies(self):
        """현재 쿠키 저장"""
        if not self.driver or not self.user_data_dir:
            return

        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            cookie_file = os.path.join(self.user_data_dir, 'cookies.pkl')

            cookies = self.driver.get_cookies()
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            print(f"💾 쿠키 저장 완료: {cookie_file}")
        except Exception as e:
            print(f"쿠키 저장 실패: {e}")

    def natural_goto(self, url: str, visit_home_first: bool = None):
        """자연스러운 페이지 방문"""
        if not self.driver:
            raise RuntimeError("드라이버가 초기화되지 않았습니다")

        if visit_home_first is None:
            visit_home_first = random.random() < 0.3

        if visit_home_first:
            base_url = '/'.join(url.split('/')[:3])
            self.driver.get(base_url)
            self._natural_pause(2, 4)
            self._random_mouse_movement()

        self.driver.get(url)
        self._natural_pause(3, 6)
        self._random_mouse_movement()

        self._natural_scroll()

    def _natural_scroll(self):
        """사람처럼 자연스럽게 스크롤"""
        if not self.driver:
            return

        scroll_count = random.randint(2, 4)
        for _ in range(scroll_count):
            scroll_amount = random.randint(300, 700)
            chunks = random.randint(3, 7)

            for i in range(chunks):
                chunk_size = scroll_amount // chunks
                self.driver.execute_script(f'window.scrollBy(0, {chunk_size})')
                time.sleep(random.uniform(0.1, 0.3))

            self._natural_pause(1, 3)

        # 가끔 위로 스크롤
        if random.random() < 0.3:
            self.driver.execute_script(f'window.scrollBy(0, -{random.randint(50, 150)})')
            self._natural_pause(0.5, 1.5)

    def _random_mouse_movement(self):
        """랜덤 마우스 움직임 (사람처럼)"""
        if not self.driver:
            return

        try:
            # 화면 크기 가져오기
            window_size = self.driver.get_window_size()
            width = window_size['width']
            height = window_size['height']

            # 시작점을 화면 중앙으로 옮겨 음수 오프셋을 방지
            center_x, center_y = width // 2, height // 2
            ActionChains(self.driver).move_by_offset(center_x, center_y).perform()
            current_x, current_y = center_x, center_y

            # 랜덤 좌표로 마우스 이동 (여러 번)
            movements = random.randint(2, 4)
            for _ in range(movements):
                target_x = random.randint(100, width - 100)
                target_y = random.randint(100, height - 100)

                ActionChains(self.driver).move_by_offset(
                    target_x - current_x,
                    target_y - current_y,
                ).perform()

                current_x, current_y = target_x, target_y
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            # 마우스 이동 실패해도 계속 진행
            pass

    def _natural_pause(self, min_sec: float = 0.5, max_sec: float = 2.0):
        """랜덤 딜레이"""
        time.sleep(random.uniform(min_sec, max_sec))

    def close(self):
        """리소스 정리 (쿠키 저장 포함)"""
        if not self.driver:
            return

        try:
            # 쿠키 저장
            self.save_cookies()
        except Exception as e:
            print(f"종료 중 오류: {e}")

        try:
            self.driver.quit()
            print("✅ 드라이버 종료 완료")
        except Exception as e:
            print(f"드라이버 종료 중 오류: {e}")
