"""
무신사 전용 크롤러 설정
"""
# CSS 선택자 설정
MUSINSA_SELECTORS = {
    # 카테고리 메뉴
    "category_icon": "svg._gnb__category--icon_vuwmc_48",  # 메뉴 열기 아이콘
    "category_modal": "div._modal_uru6o_10._modal-menu_uru6o_34",  # 하위 메뉴 모달
    
    # 상품 리스트
    "product_list": "div.GoodsList__List-sc-k7xv49-0.cqlCkb",  # 상품 리스트 컨테이너
    "product_item": "div.sc-hdBJTi.gAWtWT",  # 개별 상품 요소
    
    # 상품 정보
    "product_title": "a.gtm-select-item span",  # 상품명
    "product_price": "div.sc-jwTyAe.sc-hjsuWn.DVxSk.ANWFy",  # 가격 컨테이너 (할인율 + 가격 포함)
    "product_link": "a.gtm-select-item",  # 상품 링크
    "product_image": "img[data-mds='Image']",  # 상품 이미지
}

# 기본 설정
BASE_URL = "https://www.musinsa.com/main/musinsa/recommend?gf=A"
SCROLL_PAUSE_TIME = 2  # 무한 스크롤 대기 시간 (초)
MAX_SCROLL_ATTEMPTS = 10  # 최대 스크롤 시도 횟수


