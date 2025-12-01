"""
범용 상품 파서 모듈
HTML 구조를 동적으로 분석하여 상품 정보를 자동으로 추출합니다.
"""
import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from utils.logger import logger


@dataclass
class Product:
    """상품 정보 데이터 모델"""
    title: str          # 상품명
    price: str          # 가격
    image_url: str      # 이미지 URL
    product_url: str    # 상품 상세 링크
    product_code: str = ""  # 상품 코드 (선택)
    description: str = ""  # 상품 설명 (선택)


def parse_products(soup: BeautifulSoup, url: str = "") -> List[Product]:
    """
    HTML에서 상품 정보 자동 파싱
    
    Args:
        soup: BeautifulSoup 객체
        url: 원본 URL (상대 경로 변환용)
        
    Returns:
        추출된 상품 정보 리스트
    """
    logger.info("상품 정보 파싱 시작")
    
    # 1. 상품 리스트 탐지
    product_elements = detect_product_list(soup)
    
    if not product_elements:
        logger.warning("상품 리스트를 찾을 수 없습니다. Fallback 전략 시도")
        product_elements = parse_with_fallback(soup)
    
    if not product_elements:
        logger.error("상품 리스트 탐지 실패")
        return []
    
    logger.info(f"{len(product_elements)}개 상품 요소 발견")
    
    # 2. 각 상품 정보 추출
    products = []
    for element in product_elements:
        product = extract_product_info(element, url)
        if product and product.title:  # 제목이 있어야 유효한 상품
            products.append(product)
    
    logger.info(f"{len(products)}개 상품 정보 추출 완료")
    return products


def detect_product_list(soup: BeautifulSoup) -> List[Tag]:
    """
    HTML에서 상품 리스트 자동 탐지
    - 같은 클래스/태그가 3개 이상 반복되는 구조 찾기
    - 링크 + 이미지 조합 찾기
    - 점수 기반 최적 후보 선택
    
    Args:
        soup: BeautifulSoup 객체
        
    Returns:
        상품 요소 리스트
    """
    candidates = []
    
    # 1. 클래스 기반 반복 구조 찾기
    class_counts = {}
    for element in soup.find_all(class_=True):
        class_names = element.get('class', [])
        if class_names:
            # 클래스명 조합을 키로 사용
            class_key = ' '.join(sorted(class_names))
            class_counts[class_key] = class_counts.get(class_key, 0) + 1
    
    # 3개 이상 반복되는 클래스 찾기
    for class_key, count in class_counts.items():
        if count >= 3:
            class_list = class_key.split()
            elements = soup.find_all(class_=class_list)
            if _is_likely_product_list(elements):
                score = _calculate_list_score(elements)
                candidates.append((elements, score, "class"))
                logger.debug(f"클래스 기반 후보 발견: {class_key} ({count}개, 점수: {score:.2f})")
    
    # 2. 태그 기반 반복 구조 찾기
    tag_counts = {}
    for element in soup.find_all():
        tag_name = element.name
        if tag_name not in ['html', 'head', 'body', 'script', 'style']:
            tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
    
    for tag_name, count in tag_counts.items():
        if count >= 3:
            elements = soup.find_all(tag_name)
            if _is_likely_product_list(elements):
                score = _calculate_list_score(elements)
                candidates.append((elements, score, "tag"))
                logger.debug(f"태그 기반 후보 발견: {tag_name} ({count}개, 점수: {score:.2f})")
    
    # 3. 링크 + 이미지 조합 찾기
    links_with_images = soup.select('a:has(img)')
    if len(links_with_images) >= 3:
        # 부모 요소 찾기 (상품 컨테이너)
        parent_elements = []
        for link in links_with_images:
            parent = link.parent
            if parent and parent not in parent_elements:
                parent_elements.append(parent)
        
        if len(parent_elements) >= 3:
            score = _calculate_list_score(parent_elements)
            candidates.append((parent_elements, score, "link_image"))
            logger.debug(f"링크+이미지 조합 후보 발견: {len(parent_elements)}개, 점수: {score:.2f}")
    
    # 점수 기반 정렬 후 최적 후보 반환
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_candidate = candidates[0]
        logger.info(f"최적 상품 리스트 선택: {best_candidate[2]} 방식, 점수: {best_candidate[1]:.2f}")
        return best_candidate[0]
    
    return []


def _is_likely_product_list(elements: List[Tag]) -> bool:
    """
    요소들이 상품 리스트일 가능성 검증
    
    Args:
        elements: 검증할 요소 리스트
        
    Returns:
        상품 리스트일 가능성 여부
    """
    if len(elements) < 3:
        return False
    
    # 샘플 3개 확인
    valid_count = 0
    for elem in elements[:3]:
        has_link = elem.find('a') is not None
        has_image = elem.find('img') is not None
        has_text = len(elem.get_text(strip=True)) > 10  # 최소 10자 이상의 텍스트
        
        # 링크, 이미지, 텍스트 중 하나라도 있으면 유효
        if has_link or has_image or has_text:
            valid_count += 1
    
    # 3개 중 2개 이상이 유효하면 상품 리스트 가능성
    return valid_count >= 2


def _calculate_list_score(elements: List[Tag]) -> float:
    """
    상품 리스트 후보의 점수 계산
    
    Args:
        elements: 요소 리스트
        
    Returns:
        점수 (0.0 ~ 1.0)
    """
    if not elements:
        return 0.0
    
    score = 0.0
    
    # 샘플 5개 확인
    sample_size = min(5, len(elements))
    sample = elements[:sample_size]
    
    link_count = 0
    image_count = 0
    text_count = 0
    price_count = 0
    
    for elem in sample:
        if elem.find('a'):
            link_count += 1
        if elem.find('img'):
            image_count += 1
        text = elem.get_text(strip=True)
        if len(text) > 10:
            text_count += 1
        # 가격 패턴 확인
        if re.search(r'[\d,]+(?:\s*[원₩$€£¥]|원|₩|\$|€|£|¥)', text):
            price_count += 1
    
    # 점수 계산
    score += (link_count / sample_size) * 0.3
    score += (image_count / sample_size) * 0.3
    score += (text_count / sample_size) * 0.2
    score += (price_count / sample_size) * 0.2
    
    return min(score, 1.0)


def detect_product_title(element: Tag) -> str:
    """
    상품 요소에서 상품명 자동 인식
    
    Args:
        element: 상품 요소
        
    Returns:
        상품명
    """
    # 우선순위 1: 제목 태그 (가장 깔끔한 텍스트)
    for tag in ['h1', 'h2', 'h3', 'h4']:
        title_elem = element.find(tag)
        if title_elem:
            text = title_elem.get_text(strip=True)
            if text and len(text) >= 3:  # 최소 3자 이상
                # 가격만 제거 (제목은 유지)
                cleaned = _clean_title_text(text)
                if len(cleaned) >= 3:
                    return cleaned
                # 정제 후 너무 짧아지면 원본 반환
                elif len(text) >= 3:
                    return text
    
    # 우선순위 2: title/name 클래스
    title_patterns = [
        element.find(class_=re.compile(r'title|name|product.*name', re.I)),
        element.find(id=re.compile(r'title|name', re.I))
    ]
    for pattern in title_patterns:
        if pattern:
            text = pattern.get_text(strip=True)
            if text and len(text) >= 3:
                cleaned = _clean_title_text(text)
                if len(cleaned) >= 3:
                    return cleaned
                elif len(text) >= 3:
                    return text
    
    # 우선순위 3: 링크 텍스트 (하지만 가격/버튼 텍스트 제외)
    link = element.find('a')
    if link:
        text = link.get_text(strip=True)
        # "상세보기", "구매하기" 같은 버튼 텍스트 제외
        button_texts = ['상세보기', '구매하기', '더보기', '자세히보기', '바로가기']
        if text and text not in button_texts and len(text) >= 3:
            cleaned = _clean_title_text(text)
            if len(cleaned) >= 3:
                return cleaned
            elif len(text) >= 3:
                return text
    
    # 우선순위 4: 첫 번째 의미있는 텍스트 (가격 제외)
    text = element.get_text(strip=True)
    if text and len(text) >= 3:
        cleaned = _clean_title_text(text)
        if len(cleaned) >= 3:
            # 첫 100자만
            return cleaned[:100].strip()
        elif len(text) >= 3:
            return text[:100].strip()
    
    return ""


def _clean_title_text(text: str) -> str:
    """
    제목 텍스트 정제 (가격, 버튼 텍스트 제거)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        정제된 텍스트
    """
    # 가격 패턴 제거
    text = re.sub(r'[\d,]+(?:\s*[원₩$€£¥]|원|₩|\$|€|£|¥)', '', text).strip()
    # 버튼 텍스트 제거
    text = re.sub(r'(상세보기|구매하기|더보기|자세히보기|바로가기)', '', text).strip()
    # 연속된 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def detect_price(element: Tag) -> str:
    """
    가격 패턴 자동 인식
    
    Args:
        element: 상품 요소
        
    Returns:
        가격 문자열
    """
    # 가격 패턴 1: 숫자(쉼표 포함) + 통화 기호
    price_pattern_with_currency = r'[\d,]+(?:\s*[원₩$€£¥]|원|₩|\$|€|£|¥)'
    # 가격 패턴 2: 숫자만 (4자리 이상, 쉼표 포함 가능)
    price_pattern_number_only = r'[\d,]{4,}'
    
    # 우선순위 1: name="price" 속성을 가진 input 요소 (hidden input)
    price_input = element.find('input', {'name': re.compile(r'price|cost|amount', re.I)})
    if price_input:
        value = price_input.get('value', '').strip()
        if value:
            # name="price"인 경우는 3자리 이상도 허용 (명확한 가격 필드이므로)
            # 숫자만 있는지 확인 (쉼표 포함 가능, 최소 3자리)
            price_pattern_input = r'[\d,]{3,}'  # input의 경우 3자리 이상 허용
            match = re.search(price_pattern_input, value)
            if match:
                matched_value = match.group().strip()
                # 숫자만 있는지 확인 (쉼표 제외하고 숫자만)
                digits_only = matched_value.replace(',', '')
                if digits_only.isdigit() and len(digits_only) >= 3:
                    return matched_value
    
    # 우선순위 2: class명에 "price", "cost", "amount"가 포함된 모든 요소 찾기 및 검증
    price_candidates = []
    
    # 모든 클래스 요소 중 price 관련 클래스 찾기
    all_elements = element.find_all(class_=True)
    for elem in all_elements:
        class_names = elem.get('class', [])
        # 클래스명에 price, cost, amount가 포함되어 있는지 확인
        has_price_class = any(
            re.search(r'price|cost|amount', cls, re.I) 
            for cls in class_names
        )
        
        if has_price_class:
            text = elem.get_text(strip=True)
            if not text:
                continue
            
            # 검증 1: 통화 기호 있는 가격 패턴 (높은 신뢰도)
            match_with_currency = re.search(price_pattern_with_currency, text)
            if match_with_currency:
                price_value = match_with_currency.group().strip()
                # 클래스명 신뢰도 점수 계산
                class_score = 1.0
                if any(re.search(r'\bprice\b', cls, re.I) for cls in class_names):
                    class_score = 1.0  # "price" 정확히 포함
                elif any(re.search(r'price', cls, re.I) for cls in class_names):
                    class_score = 0.9  # "price" 부분 포함
                else:
                    class_score = 0.7  # cost, amount 등
                
                price_candidates.append({
                    'value': price_value,
                    'score': class_score + 0.2,  # 통화 기호 있으면 추가 점수
                    'source': 'class_with_currency'
                })
            
            # 검증 2: 숫자만 있는 패턴 (중간 신뢰도)
            match_number_only = re.search(price_pattern_number_only, text)
            if match_number_only:
                price_value = match_number_only.group().strip()
                # 숫자 길이로 신뢰도 조정 (4-6자리: 보통, 7자리 이상: 높음)
                num_length = len(price_value.replace(',', ''))
                length_score = min(num_length / 10.0, 0.5)  # 최대 0.5점
                
                class_score = 0.8
                if any(re.search(r'\bprice\b', cls, re.I) for cls in class_names):
                    class_score = 0.9
                elif any(re.search(r'price', cls, re.I) for cls in class_names):
                    class_score = 0.8
                else:
                    class_score = 0.6
                
                price_candidates.append({
                    'value': price_value,
                    'score': class_score + length_score,
                    'source': 'class_number_only'
                })
    
    # 후보 중 가장 높은 점수 선택
    if price_candidates:
        best_candidate = max(price_candidates, key=lambda x: x['score'])
        logger.debug(f"가격 추출: {best_candidate['value']} (점수: {best_candidate['score']:.2f}, 소스: {best_candidate['source']})")
        return best_candidate['value']
    
    # 우선순위 3: 숫자 관련 클래스 (cell_num, num 등)
    num_elem = element.find(class_=re.compile(r'num|number|cell_num', re.I))
    if num_elem:
        text = num_elem.get_text(strip=True)
        match = re.search(price_pattern_number_only, text)
        if match:
            return match.group().strip()
    
    # 우선순위 4: 전체 텍스트에서 가격 패턴 찾기 (통화 기호 있는 것 우선)
    text = element.get_text()
    matches_with_currency = re.findall(price_pattern_with_currency, text)
    if matches_with_currency:
        return max(matches_with_currency, key=len).strip()
    
    # 우선순위 5: 통화 기호 없이 숫자만 있는 경우 (4자리 이상)
    matches_number_only = re.findall(price_pattern_number_only, text)
    if matches_number_only:
        # 가장 긴 숫자 선택 (가격일 가능성이 높음)
        longest = max(matches_number_only, key=lambda x: len(x.replace(',', '')))
        # 너무 짧은 숫자 제외 (상품 ID 등일 수 있음)
        if len(longest.replace(',', '')) >= 4:
            return longest.strip()
    
    return ""


def detect_image_url(element: Tag, base_url: str = "") -> str:
    """
    이미지 URL 자동 인식
    
    Args:
        element: 상품 요소
        base_url: 기본 URL (상대 경로 변환용)
        
    Returns:
        이미지 URL
    """
    # 우선순위 1: img 태그 직접
    img = element.find('img')
    if img:
        # lazy loading 처리
        image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
        if image_url:
            return _normalize_url(image_url, base_url)
    
    # 우선순위 2: 배경 이미지
    style = element.get('style', '')
    bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
    if bg_match:
        return _normalize_url(bg_match.group(1), base_url)
    
    return ""


def detect_product_url(element: Tag, base_url: str = "") -> str:
    """
    상품 상세 링크 자동 인식
    
    Args:
        element: 상품 요소
        base_url: 기본 URL (상대 경로 변환용)
        
    Returns:
        상품 상세 링크
    """
    # a 태그 찾기
    link = element.find('a')
    if link:
        href = link.get('href')
        if href:
            return _normalize_url(href, base_url)
    
    # 요소 자체가 링크인 경우
    if element.name == 'a':
        href = element.get('href')
        if href:
            return _normalize_url(href, base_url)
    
    return ""


def detect_product_code(element: Tag) -> str:
    """
    상품 코드 자동 인식
    
    Args:
        element: 상품 요소
        
    Returns:
        상품 코드 문자열
    """
    # 우선순위 1: URL에서 상품 코드 추출 (가장 일반적)
    links = element.find_all('a', href=True)
    for link in links:
        href = link.get('href', '')
        if not href:
            continue
        
        # 다양한 URL 패턴에서 상품 코드 추출
        patterns = [
            r'num_iid=(\d+)',          # 싸다구: num_iid=846537789890
            r'product_id=(\d+)',       # product_id=12345
            r'[?&]id=(\d+)',           # id=12345 (쿼리 파라미터)
            r'item_id=(\d+)',         # item_id=12345
            r'goods_id=(\d+)',        # goods_id=12345
            r'/product/(\d+)',        # /product/12345
            r'/item/(\d+)',           # /item/12345
            r'g-(\d+)',                # Temu: g-601101921767940
            r'goods-(\d+)',            # goods-12345
            r'p-(\d+)',                # p-12345
        ]
        
        for pattern in patterns:
            match = re.search(pattern, href)
            if match:
                code = match.group(1)
                # 숫자만 있는지 확인 (최소 3자리)
                if code.isdigit() and len(code) >= 3:
                    return code
    
    # 우선순위 2: hidden input에서 상품 코드 추출
    hidden_inputs = element.find_all('input', {'type': 'hidden'})
    for inp in hidden_inputs:
        name = inp.get('name', '').lower()
        value = inp.get('value', '')
        
        # 상품 코드 관련 필드명 확인
        if any(keyword in name for keyword in ['id', 'code', 'sku', 'item', 'product', 'goods']):
            # 숫자만 있는 값인지 확인
            if value:
                # 숫자만 추출
                digits = re.findall(r'\d+', value)
                if digits:
                    # 가장 긴 숫자 선택 (상품 코드일 가능성)
                    longest = max(digits, key=len)
                    if len(longest) >= 3:
                        return longest
    
    # 우선순위 3: data 속성에서 상품 코드 추출
    for attr in element.attrs:
        if any(keyword in attr.lower() for keyword in ['id', 'code', 'sku', 'product', 'item']):
            value = element.get(attr, '')
            if value:
                # 숫자만 추출
                digits = re.findall(r'\d+', str(value))
                if digits:
                    longest = max(digits, key=len)
                    if len(longest) >= 3:
                        return longest
    
    # 우선순위 4: 요소 ID에서 추출
    elem_id = element.get('id', '')
    if elem_id:
        # ID에서 숫자 추출
        digits = re.findall(r'\d+', elem_id)
        if digits:
            longest = max(digits, key=len)
            if len(longest) >= 3:
                return longest
    
    return ""


def extract_product_info(element: Tag, base_url: str = "") -> Optional[Product]:
    """
    개별 상품 요소에서 정보 추출
    
    Args:
        element: 상품 요소
        base_url: 기본 URL
        
    Returns:
        Product 객체 또는 None
    """
    title = detect_product_title(element)
    price = detect_price(element)
    image_url = detect_image_url(element, base_url)
    product_url = detect_product_url(element, base_url)
    product_code = detect_product_code(element)
    
    # 최소한 제목은 있어야 함
    if not title:
        return None
    
    return Product(
        title=title,
        price=price,
        image_url=image_url,
        product_url=product_url or base_url,
        product_code=product_code,
        description=""
    )


def _normalize_url(url: str, base_url: str = "") -> str:
    """
    URL 정규화 (상대 경로 → 절대 경로)
    
    Args:
        url: URL 문자열
        base_url: 기본 URL
        
    Returns:
        정규화된 URL
    """
    if not url:
        return ""
    
    # 이미 절대 경로인 경우
    if url.startswith(('http://', 'https://')):
        return url
    
    # 상대 경로인 경우
    if base_url:
        return urljoin(base_url, url)
    
    return url


def parse_with_fallback(soup: BeautifulSoup) -> List[Tag]:
    """
    패턴 기반 실패 시 범용 selector 사용
    
    Args:
        soup: BeautifulSoup 객체
        
    Returns:
        상품 요소 리스트
    """
    logger.info("Fallback 전략 시도")
    
    # 범용 selector 시도
    fallback_selectors = [
        '[class*="product"]',
        '[class*="item"]',
        'article',
        '.card',
        '[class*="goods"]',
        '[class*="product-item"]'
    ]
    
    for selector in fallback_selectors:
        try:
            elements = soup.select(selector)
            if len(elements) >= 3:
                # 유효성 검증
                valid_elements = [e for e in elements if _is_likely_product_list([e])]
                if len(valid_elements) >= 3:
                    logger.info(f"Fallback 성공: {selector} ({len(valid_elements)}개)")
                    return valid_elements
        except Exception as e:
            logger.debug(f"Fallback selector 실패: {selector} - {e}")
            continue
    
    return []

