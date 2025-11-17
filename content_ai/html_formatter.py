"""
HTML 포맷터 모듈
AI2 담당
"""
from typing import Dict
from utils.logger import logger


def format_content_to_html(content: Dict) -> str:
    """
    생성된 콘텐츠를 최종 HTML 템플릿으로 변환합니다.
    
    Args:
        content: 생성된 콘텐츠 딕셔너리
        {
            "title": "...",
            "body": "...",
            "image_url": "...",
            ...
        }
        
    Returns:
        최종 HTML 문자열
    """
    logger.info("HTML 포맷팅 시작")
    
    title = content.get('title', '')
    body = content.get('body', '')
    image_url = content.get('image_url', '')
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    {f'<img src="{image_url}" alt="{title}">' if image_url else ''}
    {body}
</body>
</html>
"""
    return html.strip()


def format_for_naver_blog(content: Dict) -> str:
    """
    네이버 블로그 업로드용 HTML로 포맷팅합니다.
    
    Args:
        content: 생성된 콘텐츠 딕셔너리
        
    Returns:
        네이버 블로그용 HTML 문자열
    """
    logger.info("네이버 블로그용 HTML 포맷팅")
    # TODO: 네이버 블로그 특화 포맷팅
    return format_content_to_html(content)


def format_for_tistory_blog(content: Dict) -> str:
    """
    티스토리 블로그 업로드용 HTML로 포맷팅합니다.
    
    Args:
        content: 생성된 콘텐츠 딕셔너리
        
    Returns:
        티스토리 블로그용 HTML 문자열
    """
    logger.info("티스토리 블로그용 HTML 포맷팅")
    # TODO: 티스토리 블로그 특화 포맷팅
    return format_content_to_html(content)

