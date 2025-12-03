"""
프롬프트 빌더 모듈
AI2 담당
"""
from typing import Dict, List


def build_title_prompt(keyword: str, product_info: str = "") -> str:
    """
    제목 생성용 프롬프트를 생성합니다.

    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트

    Returns:
        제목 생성 프롬프트
    """
    prompt = f"""
다음 키워드를 기반으로 SEO 최적화되고 호기심을 유발하는 블로그 제목을 생성하세요.

키워드: {keyword}
상품 정보: {product_info}

요구사항:
- 감정어 포함 (미친 듯, 갑자기, 왜 등)
- 숫자/통계 활용 가능
- 30자 이내
- 광고 느낌 최소화

제목 3개를 생성해주세요.
"""
    return prompt.strip()


def build_outline_prompt(keyword: str, title: str, product_info: str = "") -> str:
    """
    아웃라인 생성용 프롬프트를 생성합니다.

    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        product_info: 상품 정보 텍스트

    Returns:
        아웃라인 생성 프롬프트
    """
    prompt = f"""
다음 정보를 바탕으로 블로그 글의 아웃라인을 생성하세요.

제목: {title}
키워드: {keyword}
상품 정보: {product_info}

요구사항:
- 5~7개 섹션으로 구성
- h2, h3 태그 구조 포함
- 각 섹션별 간단한 설명 포함

아웃라인을 JSON 형식으로 제공해주세요.
"""
    return prompt.strip()


def format_outline_for_prompt(outline: Dict) -> str:
    """
    아웃라인 딕셔너리를 읽기 쉬운 텍스트 형식으로 변환

    Args:
        outline: 아웃라인 딕셔너리

    Returns:
        포맷팅된 아웃라인 텍스트
    """
    if not outline or "h2" not in outline:
        return "아웃라인 없음"

    lines = []
    for h2_item in outline["h2"]:
        h2_title = h2_item.get("title", "")
        lines.append(f"h2: {h2_title}")

        h3_list = h2_item.get("h3", [])
        for h3_title in h3_list:
            lines.append(f"  h3: {h3_title}")

    return "\n".join(lines)


def build_body_prompt(
    keyword: str, title: str, outline: Dict, product_info: str = ""
) -> str:
    """
    본문 생성용 프롬프트를 생성합니다.

    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인
        product_info: 상품 정보 텍스트

    Returns:
        본문 생성 프롬프트
    """
    prompt = f"""
다음 정보를 바탕으로 자연스럽고 읽기 쉬운 블로그 본문을 생성하세요.

제목: {title}
키워드: {keyword}
아웃라인: {outline}
상품 정보: {product_info}

요구사항:
- 1,000~1,500자 분량
- h2, h3 태그 포함
- 자연스럽고 광고 느낌 없는 문체
- SEO 최적화
- 키워드 자연스럽게 배치

HTML 형식으로 본문을 생성해주세요.
"""
    return prompt.strip()

