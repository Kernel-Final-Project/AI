"""
크롬 드라이버 초기화 및 공통 유틸
"""
from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from .logger import logger


def build_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """
    공통 크롬 드라이버를 구성한다.
    """
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--lang=ko-KR")
    if headless:
        options.add_argument("--headless")

    logger.info("Chrome 드라이버 초기화 (headless=%s)", headless)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 봇 감지 회피
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def wait_for(driver: webdriver.Chrome, condition, timeout: int | None = None):
    """
    WebDriverWait 헬퍼.
    """
    if timeout is None:
        timeout = 10
    return WebDriverWait(driver, timeout).until(condition)


def wait_presence(driver: webdriver.Chrome, locator, timeout: int | None = None):
    return wait_for(driver, EC.presence_of_element_located(locator), timeout)
