"""
프롬프트 빌더 모듈
AI2 담당
"""
from pathlib import Path
from typing import Dict
from utils.logger import logger


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


def load_prompt(prompt_name: str) -> str:
    """
    프롬프트 파일을 로드합니다.
    
    Args:
        prompt_name: 프롬프트 파일명 (확장자 제외, 예: "title_prompt")
        
    Returns:
        프롬프트 파일 내용 (파일이 없으면 빈 문자열)
    """
    try:
        # content_ai/prompts/ 디렉토리에서 파일 찾기
        prompts_dir = Path(__file__).parent / "prompts"
        prompt_file = prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_file.exists():
            logger.error(f"프롬프트 파일을 찾을 수 없습니다: {prompt_file}")
            return ""
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"프롬프트 파일 로드 완료: {prompt_name}")
        return content.strip()
        
    except Exception as e:
        logger.error(f"프롬프트 파일 로드 중 오류 발생: {e}")
        return ""

