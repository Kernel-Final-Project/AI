BASE_URL = "https://www.musinsa.com"

# ✅ 1) 상단 카테고리 버튼
XPATH_CATEGORY_BUTTON = "//button[contains(., '카테고리') or contains(., 'CATEGORY')]"

# ✅ 2) 상위 카테고리 (개선: ul[1] 제거)
XPATH_TOP_CATEGORY_ITEMS = "//nav//ul/li/a"
# 또는 더 안정적으로
XPATH_TOP_CATEGORY_ITEMS = "//nav//li/a[contains(@href, '/category') or @data-category-id]"

# ✅ 3) 하위 카테고리 (좋음)
XPATH_SUBCATEGORY_ITEMS_REL = ".//ul/li/a"

# ✅ 4) 상품 카드 (개선: data 속성 추가)
XPATH_PRODUCT_CARD = "//div[contains(@class, 'list-box') or contains(@class, 'li_box') or @data-item-id]"

# ✅ 5) 상품 정보 (좋음, data 속성 추가 고려)
XPATH_PRODUCT_TITLE_REL = ".//p[contains(@class, 'list_info')]/a | .//a[@data-item-id]"
XPATH_PRODUCT_PRICE_REL = ".//p[contains(@class, 'price')]"
XPATH_PRODUCT_IMAGE_REL = ".//img[@src or @data-src]"