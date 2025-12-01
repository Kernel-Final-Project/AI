"""
SSR/CSR 판별 모듈
URL을 받아서 서버 사이드 렌더링(SSR) 또는 클라이언트 사이드 렌더링(CSR) 여부를 판별합니다.
"""
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from utils.logger import logger


@dataclass
class CheckResult:
    """SSR/CSR 판별 결과"""
    url: str
    rendering_type: str  # "SSR", "CSR", "HYBRID", "UNKNOWN"
    has_content: bool  # requests로 받은 HTML에 실제 콘텐츠가 있는지
    script_count: int  # <script> 태그 개수
    api_endpoints: List[str]  # 발견된 API 엔드포인트
    json_data: bool  # JSON 데이터 포함 여부
    confidence: float  # 판별 신뢰도 (0.0 ~ 1.0)


def check_ssr_csr(url: str, timeout: int = 10) -> CheckResult:
    """
    URL의 SSR/CSR 여부를 판별합니다.
    
    Args:
        url: 확인할 URL
        timeout: 요청 타임아웃 (초)
        
    Returns:
        CheckResult 객체
    """
    logger.info(f"SSR/CSR 판별 시작: {url}")
    
    try:
        # User-Agent 설정 (일부 사이트에서 차단 방지)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # requests로 HTML 가져오기
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        html = response.text
        
        # HTML 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 실제 콘텐츠 포함 여부 확인
        has_content = _check_content_presence(soup)
        
        # 2. <script> 태그 분석
        scripts = soup.find_all('script')
        script_count = len(scripts)
        
        # 3. API 엔드포인트 찾기
        api_endpoints = _find_api_endpoints(html, scripts)
        
        # 4. JSON 데이터 포함 여부
        has_json_data = _check_json_data(html, scripts)
        
        # 5. 판별 로직
        rendering_type, confidence = _determine_rendering_type(
            has_content, script_count, api_endpoints, has_json_data
        )
        
        result = CheckResult(
            url=url,
            rendering_type=rendering_type,
            has_content=has_content,
            script_count=script_count,
            api_endpoints=api_endpoints[:10],  # 최대 10개만
            json_data=has_json_data,
            confidence=confidence
        )
        
        logger.info(f"판별 완료: {rendering_type} (신뢰도: {confidence:.2f})")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"요청 실패: {e}")
        return CheckResult(
            url=url,
            rendering_type="UNKNOWN",
            has_content=False,
            script_count=0,
            api_endpoints=[],
            json_data=False,
            confidence=0.0
        )
    except Exception as e:
        logger.error(f"판별 중 오류 발생: {e}")
        return CheckResult(
            url=url,
            rendering_type="UNKNOWN",
            has_content=False,
            script_count=0,
            api_endpoints=[],
            json_data=False,
            confidence=0.0
        )


def _check_content_presence(soup: BeautifulSoup) -> bool:
    """
    HTML에 실제 콘텐츠가 포함되어 있는지 확인합니다.
    
    Args:
        soup: BeautifulSoup 객체
        
    Returns:
        콘텐츠 포함 여부
    """
    # 일반적인 콘텐츠 선택자들
    content_selectors = [
        'article', 'main', '.content', '#content',
        '.product', '.item', '.product-item',
        'h1', 'h2', 'h3',
        'p', 'div[class*="product"]', 'div[class*="item"]'
    ]
    
    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            # 텍스트가 있는지 확인
            for elem in elements[:5]:  # 처음 5개만 확인
                text = elem.get_text(strip=True)
                if len(text) > 20:  # 의미있는 텍스트 길이
                    return True
    
    # body 텍스트 확인
    body = soup.find('body')
    if body:
        text = body.get_text(strip=True)
        if len(text) > 100:  # 충분한 텍스트가 있으면 SSR 가능성
            return True
    
    return False


def _find_api_endpoints(html: str, scripts: List) -> List[str]:
    """
    HTML과 스크립트에서 API 엔드포인트를 찾습니다.
    
    Args:
        html: HTML 문자열
        scripts: <script> 태그 리스트
        
    Returns:
        발견된 API 엔드포인트 리스트
    """
    endpoints = []
    
    # 일반적인 API 패턴
    patterns = [
        r'["\']([^"\']*api[^"\']*)["\']',  # "api/..." 또는 'api/...'
        r'fetch\(["\']([^"\']+)["\']',  # fetch("...")
        r'axios\.(get|post)\(["\']([^"\']+)["\']',  # axios.get("...")
        r'\.ajax\(["\']([^"\']+)["\']',  # $.ajax("...")
        r'url:\s*["\']([^"\']+)["\']',  # url: "..."
    ]
    
    # HTML에서 검색
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[-1]  # 그룹이 여러 개면 마지막 것
            if match and match.startswith(('http', '/', './')):
                endpoints.append(match)
    
    # <script> 태그 내용에서 검색
    for script in scripts:
        if script.string:
            for pattern in patterns:
                matches = re.findall(pattern, script.string, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[-1]
                    if match and match.startswith(('http', '/', './')):
                        endpoints.append(match)
    
    # 중복 제거
    return list(set(endpoints))


def _check_json_data(html: str, scripts: List) -> bool:
    """
    HTML이나 스크립트에 JSON 데이터가 포함되어 있는지 확인합니다.
    
    Args:
        html: HTML 문자열
        scripts: <script> 태그 리스트
        
    Returns:
        JSON 데이터 포함 여부
    """
    # JSON 패턴 (간단한 확인)
    json_patterns = [
        r'\{[^{}]*"[^"]*"\s*:\s*[^,}]+\}',  # 간단한 JSON 객체
        r'\[[^\[\]]*\{[^}]*\}[^\[\]]*\]',  # JSON 배열
    ]
    
    # HTML에서 검색
    for pattern in json_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    
    # <script> 태그에서 검색
    for script in scripts:
        if script.string:
            # window.__INITIAL_STATE__ 같은 패턴
            if re.search(r'window\.__[A-Z_]+__\s*=', script.string):
                return True
            # JSON.parse 패턴
            if re.search(r'JSON\.parse\(', script.string):
                return True
    
    return False


def _determine_rendering_type(
    has_content: bool,
    script_count: int,
    api_endpoints: List[str],
    has_json_data: bool
) -> Tuple[str, float]:
    """
    판별 결과를 종합하여 렌더링 타입을 결정합니다.
    
    Args:
        has_content: 콘텐츠 포함 여부
        script_count: 스크립트 개수
        api_endpoints: API 엔드포인트 리스트
        has_json_data: JSON 데이터 포함 여부
        
    Returns:
        (rendering_type, confidence) 튜플
    """
    ssr_score = 0.0
    csr_score = 0.0
    
    # SSR 지표
    if has_content:
        ssr_score += 0.5
    if script_count < 10:  # 스크립트가 적으면 SSR 가능성
        ssr_score += 0.2
    if not api_endpoints:
        ssr_score += 0.2
    
    # CSR 지표
    if not has_content:
        csr_score += 0.5
    if script_count > 5:  # 스크립트가 많으면 CSR 가능성
        csr_score += 0.2
    if api_endpoints:
        csr_score += 0.3
    if has_json_data:
        csr_score += 0.2
    
    # 판별
    if ssr_score > csr_score and ssr_score >= 0.5:
        confidence = min(ssr_score, 0.9)
        return "SSR", confidence
    elif csr_score > ssr_score and csr_score >= 0.5:
        confidence = min(csr_score, 0.9)
        return "CSR", confidence
    elif ssr_score > 0.3 and csr_score > 0.3:
        confidence = (ssr_score + csr_score) / 2
        return "HYBRID", confidence
    else:
        return "UNKNOWN", 0.3

