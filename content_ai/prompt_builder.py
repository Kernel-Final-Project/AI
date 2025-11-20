"""
프롬프트 빌더 모듈
AI2 담당
"""
import pathlib
from typing import Dict, List

PROMPT_DIR = pathlib.Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """
    프롬프트 파일을 로드합니다.
    
    Args:
        name: 프롬프트 파일명 (확장자 제외)
        
    Returns:
        프롬프트 텍스트
    """
    file_path = PROMPT_DIR / f"{name}.txt"
    return file_path.read_text(encoding="utf-8")


def build_title_prompt(keyword: str, product_info: str = "") -> str:
    """
    제목 생성용 프롬프트를 생성합니다.
    
    Args:
        keyword: 선택된 키워드
        product_info: 상품 정보 텍스트
        
    Returns:
        제목 생성 프롬프트
    """
    template = load_prompt("title_prompt")
    return template.format(keyword=keyword, product_info=product_info)


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
    template = load_prompt("outline_prompt")
    return template.format(keyword=keyword, title=title, product_info=product_info)


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


def build_body_prompt(keyword: str, title: str, outline: Dict, product_info: str = "") -> str:
    """
    본문 생성용 프롬프트를 생성합니다.
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        outline: 생성된 아웃라인 (딕셔너리)
        product_info: 상품 정보 텍스트
        
    Returns:
        본문 생성 프롬프트
    """
    template = load_prompt("content_prompt")
    # outline을 읽기 쉬운 형식으로 변환
    outline_str = format_outline_for_prompt(outline) if isinstance(outline, dict) else str(outline)
    return template.format(
        keyword=keyword,
        title=title,
        outline=outline_str,
        product_info=product_info if product_info else "없음"
    )

