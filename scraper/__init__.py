"""
범용 HTML 크롤링 모듈
다양한 쇼핑몰 사이트에서 SSR/CSR을 자동 판별하고 HTML을 추출합니다.
"""
from scraper.html_extractor import extract_html, load_html_ssr, load_html_csr
from scraper.ssr_csr_checker import check_ssr_csr, CheckResult
from scraper.category_interaction import (
    hover_element, 
    hover_and_wait_for_submenu,
    find_selenium_element,
    scroll_to_element
)

__all__ = [
    'extract_html', 'load_html_ssr', 'load_html_csr', 
    'check_ssr_csr', 'CheckResult',
    'hover_element', 'hover_and_wait_for_submenu',
    'find_selenium_element', 'scroll_to_element'
]

