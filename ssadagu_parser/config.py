"""
싸다구 전용 크롤러 설정
"""
# CSS 선택자 설정
SSADAGU_SELECTORS = {
    # 상품 리스트 컨테이너
    "product_list": "div.product_info",
    
    # 개별 상품 정보
    "product_title": "div.product_title",
    "product_price": "div.product_price",
    "product_image": "div.product-image-container img.hover-big",  # product-image-container 내부의 hover-big 이미지
    "product_image_container": "div.product-image-container",  # 이미지 컨테이너
    "product_link": "a[href*='view.php']",
    
    # 카테고리 (나중에 사용)
    "category_container": "div.all_cate",
    "category_link": "a.cate_tit",
}

# 기본 설정
BASE_URL = "https://ssadagu.kr"
SCROLL_PAUSE_TIME = 2  # 무한 스크롤 대기 시간 (초)
MAX_SCROLL_ATTEMPTS = 10  # 최대 스크롤 시도 횟수

