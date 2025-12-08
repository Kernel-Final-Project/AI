"""
쇼핑몰별 URL 패턴 정의
"""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

@dataclass
class URLPattern:
    """쇼핑몰 URL 패턴"""
    domain: str
    search_template: str
    name: str

    def build_search_url(self, keyword: str) -> str:
        """ 키워드로 검색 URL 생성 """
        encoded_keyword = quote(keyword)
        return self.search_template.format(keyword=encoded_keyword)
    
# 주요 쇼핑몰 URL 패턴 정의
SHOPPING_PATTERNS = [
    URLPattern(
        domain="musinsa.com",
        search_template="https://www.musinsa.com/search/goods?keyword={keyword}",
        name="무신사"
    ),
    URLPattern(
        domain="ssadagu.kr",
        search_template="https://ssadagu.kr/shop/search.php?ss_tx={keyword}",
        name="싸다구"
    ),
    URLPattern(
          domain="gmarket.co.kr",
          search_template="https://browse.gmarket.co.kr/search?keyword={keyword}",
          name="G마켓"
      ),
    URLPattern(
        domain="zigzag.kr",
        search_template="https://zigzag.kr/search?keyword={keyword}",
        name="지그재그"
    ),
    URLPattern(
        domain="29cm.co.kr",
        search_template="https://shop.29cm.co.kr/search?keyword={keyword}",
        name="29CM"
    ),
    URLPattern(
        domain="11st.co.kr",
        search_template="https://search.11st.co.kr/pc/total-search?kwd={keyword}",
        name="11번가"
    ),
    URLPattern(
        domain="ssg.com",
        search_template="https://www.ssg.com/search.ssg?target=all&query={keyword}",
        name="SSG"
    ),
    URLPattern(
        domain="kream.co.kr",
        search_template="https://kream.co.kr/search?keyword={keyword}",
        name="kream"
    ),
    URLPattern(
        domain="oliveyoung.co.kr",
        search_template="https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={keyword}",
        name="oliveyoung"
    ),
    URLPattern(
        domain="eqlstore.com",
        search_template="https://www.eqlstore.com/public/search/view?searchWord={keyword}",
        name="EQL"
    ),
    URLPattern(
        domain="www.coupang.com",
        search_template="https://www.coupang.com/np/search?component=&q={keyword}",
        name="coupang"
    ),
]

def find_pattern_by_url(url: str) -> Optional[URLPattern]:
    """URL에서 쇼핑몰 패턴 찾기"""
    url_lower = url.lower()
    for pattern in SHOPPING_PATTERNS:
        if pattern.domain in url_lower:
            return pattern
    return None

def find_pattern_by_domain(domain: str) -> Optional[URLPattern]:
    """ 도메인으로 쇼핑몰 패턴 찾기 """
    doamin_lower = domain.lower
    for pattern in SHOPPING_PATTERNS:
        if pattern.domain in doamin_lower:
            return pattern
    return None