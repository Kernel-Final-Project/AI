"""
아웃라인 생성 모듈
AI2 담당
"""
import json
import time
from typing import Dict, List, Optional
from content_ai.gpt_utils import generate_with_prompt, parse_json_response
from utils.logger import logger


def generate_outlines(keyword: str, title: str, product_info: str = "", max_retries: int = 2) -> Optional[Dict]:
    """
    GPT로 아웃라인 생성 (재시도 로직 포함)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 아웃라인 딕셔너리 (실패 시 None)
    """
    logger.info(f"아웃라인 생성 시작: {keyword} - {title}")
    
    for attempt in range(max_retries):
        try:
            # GPT 호출
            response = generate_with_prompt(
                prompt_name="outline_prompt",
                user_data={
                    "키워드": keyword,
                    "제목": title,
                    "상품 정보": product_info if product_info else "없음"
                },
                temperature=0.7,
                max_retries=2
            )
            
            if not response:
                logger.warning(f"GPT 응답 없음. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
            
            # GPT 원본 응답 로그
            logger.info(f"GPT 원본 응답 (시도 {attempt+1}):\n{response[:1000]}...")
            
            # JSON 파싱
            outline = parse_outline_from_response(response)
            
            # 파싱된 아웃라인 상세 로그
            if outline and "h2" in outline:
                logger.info(f"파싱된 아웃라인: h2 {len(outline['h2'])}개")
                for i, h2_item in enumerate(outline["h2"], 1):
                    h2_title = h2_item.get("title", "")
                    h3_list = h2_item.get("h3", [])
                    logger.info(f"  h2[{i}]: {h2_title} (h3: {len(h3_list)}개)")
                    for j, h3_title in enumerate(h3_list, 1):
                        logger.info(f"    h3[{j}]: {h3_title}")
            else:
                logger.warning(f"아웃라인 파싱 실패 또는 구조 오류")
            
            # 아웃라인 검증
            if validate_outline(outline, keyword):
                logger.info(f"아웃라인 생성 완료: h2 {len(outline.get('h2', []))}개")
                return outline
            else:
                # 검증 실패 시 상세 정보 출력
                h2_count = len(outline.get('h2', [])) if outline else 0
                logger.warning(f"아웃라인 검증 실패 (h2: {h2_count}개). 재시도 ({attempt+1}/{max_retries})")
                if outline and "h2" in outline:
                    # 모든 h2 제목 상세 정보 출력
                    for i, h2_item in enumerate(outline["h2"], 1):
                        h2_title = h2_item.get("title", "")
                        if keyword in h2_title:
                            remaining = h2_title.replace(keyword, "").strip()
                            logger.warning(f"  h2[{i}]: '{h2_title}' (전체: {len(h2_title)}자, 키워드 제외: {len(remaining)}자)")
                        else:
                            logger.warning(f"  h2[{i}]: '{h2_title}' (전체: {len(h2_title)}자, 키워드 미포함)")
            
            # 재시도 전 대기
            if attempt < max_retries - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"아웃라인 생성 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
    
    logger.error(f"아웃라인 생성 실패: 최대 재시도 횟수({max_retries}) 초과")
    return None


def parse_markdown_outline(markdown_text: str) -> Dict:
    """
    Markdown 형식의 h2/h3 구조를 JSON으로 변환
    
    Args:
        markdown_text: Markdown 형식 텍스트 (## h2, ### h3)
        
    Returns:
        아웃라인 딕셔너리 (파싱 실패 시 빈 딕셔너리)
    """
    try:
        h2_list = []
        current_h2 = None
        
        lines = markdown_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # h3 제목 파싱 (### 먼저 체크 - ###가 ##에 포함되므로)
            if line.startswith('###'):
                if current_h2 is None:
                    # h2 없이 h3가 나온 경우, 빈 h2 생성
                    current_h2 = {
                        "title": "",
                        "h3": []
                    }
                
                h3_title = line[3:].strip()  # ### 제거
                h3_title = h3_title.strip(' #')
                if h3_title:
                    current_h2["h3"].append(h3_title)
            
            # h2 제목 파싱 (## - ###가 아닌 경우만)
            elif line.startswith('##'):
                # 기존 h2가 있으면 리스트에 추가
                if current_h2 is not None:
                    h2_list.append(current_h2)
                
                # 새 h2 시작
                h2_title = line[2:].strip()  # ## 제거
                # 앞뒤 공백 및 특수문자 제거
                h2_title = h2_title.strip(' #')
                if h2_title:
                    current_h2 = {
                        "title": h2_title,
                        "h3": []
                    }
        
        # 마지막 h2 추가
        if current_h2 is not None:
            h2_list.append(current_h2)
        
        if h2_list:
            logger.info(f"Markdown 파싱 성공: h2 {len(h2_list)}개")
            return {"h2": h2_list}
        else:
            logger.warning("Markdown 파싱 결과 h2가 없음")
            return {}
            
    except Exception as e:
        logger.error(f"Markdown 파싱 중 오류: {e}")
        return {}


def parse_outline_from_response(response: str) -> Dict:
    """
    GPT 응답에서 아웃라인 딕셔너리 추출 (JSON 또는 Markdown 형식 지원)
    
    Args:
        response: GPT 응답 텍스트 (JSON 또는 Markdown 형식)
        
    Returns:
        아웃라인 딕셔너리 (파싱 실패 시 빈 딕셔너리)
    """
    try:
        # 1. JSON 파싱 시도
        parsed = parse_json_response(response)
        
        # "h2" 키가 있는지 확인
        if "h2" in parsed and isinstance(parsed["h2"], list):
            return parsed
        
        # "raw" 키가 있으면 JSON 파싱 실패한 경우
        raw_text = parsed.get("raw", response) if "raw" in parsed else response
        
        # 코드 블록 제거 시도
        if "```json" in raw_text:
            start = raw_text.find("```json") + 7
            end = raw_text.find("```", start)
            if end != -1:
                raw_text = raw_text[start:end].strip()
        elif "```markdown" in raw_text:
            start = raw_text.find("```markdown") + 11
            end = raw_text.find("```", start)
            if end != -1:
                raw_text = raw_text[start:end].strip()
        elif "```" in raw_text:
            start = raw_text.find("```") + 3
            end = raw_text.find("```", start)
            if end != -1:
                raw_text = raw_text[start:end].strip()
        
        # 설명 텍스트가 포함된 경우 JSON 추출 시도
        # { 로 시작하는 부분 찾기
        json_start = raw_text.find('{')
        if json_start != -1:
            # { 부터 시작해서 닫는 } 찾기 (중첩 고려)
            brace_count = 0
            json_end = -1
            for i in range(json_start, len(raw_text)):
                if raw_text[i] == '{':
                    brace_count += 1
                elif raw_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end != -1:
                json_text = raw_text[json_start:json_end]
                try:
                    json_result = json.loads(json_text)
                    if "h2" in json_result and isinstance(json_result["h2"], list):
                        logger.info("설명 텍스트에서 JSON 추출 성공")
                        return json_result
                except:
                    pass
        
        # 다시 전체 raw_text에서 JSON 파싱 시도
        try:
            json_result = json.loads(raw_text)
            if "h2" in json_result and isinstance(json_result["h2"], list):
                return json_result
        except:
            pass
        
        # 2. JSON 파싱 실패 시 Markdown 파싱 시도
        if "##" in raw_text or "###" in raw_text:
            logger.info("Markdown 형식으로 파싱 시도")
            markdown_result = parse_markdown_outline(raw_text)
            if markdown_result and "h2" in markdown_result:
                return markdown_result
        
        # 원본 응답에서도 Markdown 파싱 시도
        if "##" in response or "###" in response:
            logger.info("원본 응답에서 Markdown 형식으로 파싱 시도")
            markdown_result = parse_markdown_outline(response)
            if markdown_result and "h2" in markdown_result:
                return markdown_result
        
        logger.warning("아웃라인 구조가 올바르지 않음")
        return {}
        
    except Exception as e:
        logger.error(f"아웃라인 파싱 중 오류: {e}")
        return {}


def validate_outline(outline: Dict, keyword: str) -> bool:
    """
    생성된 아웃라인 검증
    
    Args:
        outline: 아웃라인 딕셔너리
        keyword: 원본 키워드
        
    Returns:
        검증 통과 여부
    """
    if not outline or "h2" not in outline:
        logger.warning("아웃라인에 h2 섹션이 없습니다.")
        return False
    
    h2_list = outline["h2"]
    
    # 1. h2 개수 검증 (3~5개)
    if not isinstance(h2_list, list) or len(h2_list) < 3 or len(h2_list) > 5:
        logger.warning(f"h2 개수가 올바르지 않습니다. (현재: {len(h2_list) if isinstance(h2_list, list) else 0}개, 요구: 3~5개)")
        return False
    
    # 2. 각 h2 구조 검증
    keyword_count = 0  # 키워드 포함된 h2 개수
    
    for i, h2_item in enumerate(h2_list):
        if not isinstance(h2_item, dict) or "title" not in h2_item:
            logger.warning(f"h2[{i}] 구조가 올바르지 않습니다.")
            return False
        
        h2_title = h2_item["title"]
        
        # h2 제목 길이 검증 (키워드 제외 나머지 텍스트 기준)
        # 키워드 제외 나머지: 최대 12자까지 허용, 전체: 최대 20자까지 허용
        if keyword in h2_title:
            remaining_text = h2_title.replace(keyword, "").strip()
            remaining_length = len(remaining_text)
            if remaining_length > 12 or len(h2_title) > 20:
                logger.warning(f"h2[{i}] 제목 길이 초과: '{h2_title}' (전체: {len(h2_title)}자, 키워드 제외: {remaining_length}자, 요구: 키워드 제외 12자 이하, 전체 20자 이하)")
                return False
            if len(h2_title) < 6:
                logger.warning(f"h2[{i}] 제목이 너무 짧습니다: '{h2_title}' (전체: {len(h2_title)}자, 요구: 6자 이상)")
                return False
        else:
            # 키워드가 없으면 전체 길이로 검증 (6자 이상 17자 이하)
            if len(h2_title) < 6 or len(h2_title) > 17:
                logger.warning(f"h2[{i}] 제목이 6자 미만이거나 17자 초과입니다. (현재: {len(h2_title)}자, 요구: 6자 이상 17자 이하)")
                return False
        
        # 키워드 포함 여부 확인
        if keyword in h2_title:
            keyword_count += 1
        
        # h3 검증
        if "h3" not in h2_item:
            logger.warning(f"h2[{i}]에 h3가 없습니다.")
            return False
        
        h3_list = h2_item["h3"]
        
        if not isinstance(h3_list, list) or len(h3_list) < 1 or len(h3_list) > 2:
            logger.warning(f"h2[{i}]의 h3 개수가 올바르지 않습니다. (현재: {len(h3_list) if isinstance(h3_list, list) else 0}개, 요구: 1~2개)")
            return False
        
        # 각 h3 제목 길이 검증
        for j, h3_title in enumerate(h3_list):
            if not isinstance(h3_title, str):
                logger.warning(f"h2[{i}].h3[{j}]가 문자열이 아닙니다.")
                return False
            
            # h3 제목 길이 검증 (키워드 제외 나머지 텍스트 기준)
            # 키워드 제외 나머지: 최대 12자까지 허용, 전체: 최대 20자까지 허용
            if keyword in h3_title:
                remaining_text = h3_title.replace(keyword, "").strip()
                remaining_length = len(remaining_text)
                if remaining_length > 12 or len(h3_title) > 20:
                    logger.warning(f"h2[{i}].h3[{j}] 제목 길이 초과: '{h3_title}' (전체: {len(h3_title)}자, 키워드 제외: {remaining_length}자, 요구: 키워드 제외 12자 이하, 전체 20자 이하)")
                    return False
                if len(h3_title) < 6:
                    logger.warning(f"h2[{i}].h3[{j}] 제목이 너무 짧습니다: '{h3_title}' (전체: {len(h3_title)}자, 요구: 6자 이상)")
                    return False
            else:
                # 키워드가 없으면 전체 길이로 검증 (6자 이상 17자 이하)
                if len(h3_title) < 6 or len(h3_title) > 17:
                    logger.warning(f"h2[{i}].h3[{j}] 제목이 6자 미만이거나 17자 초과입니다. (현재: {len(h3_title)}자, 요구: 6자 이상 17자 이하)")
                    return False
    
    # 3. 키워드 포함 여부 검증 (2~4개 h2에 포함)
    if keyword_count < 2:
        logger.warning(f"키워드가 포함된 h2가 부족합니다. (현재: {keyword_count}개, 요구: 2~4개)")
        return False
    
    logger.info(f"아웃라인 검증 통과: h2 {len(h2_list)}개, 키워드 포함 h2 {keyword_count}개")
    return True


def create_fallback_outline(keyword: str, title: str, product_info: str = "") -> Dict:
    """
    모든 시도 실패 시 기본 아웃라인 생성 (폴백 메커니즘)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        product_info: 상품 정보 텍스트
        
    Returns:
        기본 아웃라인 딕셔너리
    """
    # 기본 템플릿: 개요 → 특징 → 활용 → 비교 → 결론 (7자 이상 15자 미만)
    fallback_outline = {
        "h2": [
            {
                "title": f"{keyword} 개요 정보",
                "h3": [f"{keyword} 기본 정보"]
            },
            {
                "title": f"{keyword} 특징 분석",
                "h3": [f"{keyword} 주요 특징", f"{keyword} 장점 분석"]
            },
            {
                "title": f"{keyword} 활용 방법",
                "h3": [f"{keyword} 사용 방법"]
            },
            {
                "title": f"{keyword} 비교 분석",
                "h3": [f"{keyword} 선택 가이드"]
            },
            {
                "title": "최종 결론 및 정리",
                "h3": ["마무리 정리 및 안내"]
            }
        ]
    }
    
    logger.warning(f"폴백 아웃라인 생성: h2 {len(fallback_outline['h2'])}개")
    return fallback_outline


def generate_outline(keyword: str, title: str, product_info: str = "", max_retries: int = 2) -> Dict:
    """
    아웃라인 생성 통합 함수 (전체 프로세스 재시도 포함)
    
    Args:
        keyword: 선택된 키워드
        title: 생성된 제목
        product_info: 상품 정보 텍스트
        max_retries: 최대 재시도 횟수 (기본값: 3)
        
    Returns:
        생성된 아웃라인 딕셔너리 (실패 시 폴백 아웃라인)
    """
    for attempt in range(max_retries):
        try:
            # 1. 아웃라인 생성
            outline = generate_outlines(keyword, title, product_info, max_retries=2)
            
            if not outline:
                logger.warning(f"아웃라인 생성 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
            
            # 2. 검증 (generate_outlines 내부에서 이미 검증하지만, 한 번 더 확인)
            if validate_outline(outline, keyword):
                logger.info(f"아웃라인 생성 성공: h2 {len(outline.get('h2', []))}개")
                return outline
            else:
                logger.warning(f"아웃라인 검증 실패. 재시도 ({attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
                
        except Exception as e:
            logger.error(f"아웃라인 생성 프로세스 중 예외 발생: {e}. 재시도 ({attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    # 모든 재시도 실패 시 폴백 아웃라인 반환
    logger.error(f"아웃라인 생성 최종 실패: 최대 재시도 횟수({max_retries}) 초과. 폴백 아웃라인 사용")
    return create_fallback_outline(keyword, title, product_info)

