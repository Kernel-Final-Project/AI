"""
HTML에서 카테고리 메뉴를 탐지하는 모듈
패턴 기반 필터링을 통해 카테고리 후보를 찾습니다.
"""
from typing import List
from bs4 import BeautifulSoup, Tag
from utils.category_patterns import (
    CATEGORY_CLASS_KEYWORDS,
    CATEGORY_ID_KEYWORDS,
    CATEGORY_TAGS
)


def find_category_candidates(html: str):
    """
    HTML에서 카테고리 메뉴일 가능성이 높은 요소를 찾아 반환한다.
    패턴 기반 필터링 (class/id/tag 기반).
    
    Args:
        html: HTML 문자열
        
    Returns:
        카테고리 후보 요소 리스트 (BeautifulSoup Tag 객체)
    """
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    # 모든 태그 순회
    for tag in soup.find_all(True):
        tag_name = tag.name.lower()
        classes = tag.get("class", [])
        element_id = tag.get("id", "")
        # -------------------------------
        # ① 태그 이름이 CATEGORY_TAGS에 포함되면 기본 후보
        # -------------------------------
        tag_match = tag_name in CATEGORY_TAGS
        # -------------------------------
        # ② class 기반 패턴 매칭
        # -------------------------------
        class_match = False
        if classes:
            class_str = " ".join(classes).lower()
            class_match = any(keyword in class_str for keyword in CATEGORY_CLASS_KEYWORDS)
        # -------------------------------
        # ③ id 기반 패턴 매칭
        # -------------------------------
        id_match = False
        if element_id:
            id_match = any(keyword in element_id.lower() for keyword in CATEGORY_ID_KEYWORDS)
        # -------------------------------
        # 후보 조건
        # 하나라도 매칭되면 카테고리 후보로 인정
        # -------------------------------
        if tag_match or class_match or id_match:
            candidates.append(tag)
    return candidates


def filter_clickable_elements(candidates: List[Tag]) -> List[Tag]:
    """
    정적 HTML에서 '클릭 가능한 요소'만 필터링한다.
    
    클릭 가능으로 인정되는 조건:
    - <a> 태그 자체
    - 내부에 <a> 포함된 요소 (li, div 등)
    - onclick 속성 존재
    - role='button' 또는 class='btn' 포함
    - cursor:pointer 스타일 포함
    
    Args:
        candidates: 필터링할 카테고리 후보 리스트 (BeautifulSoup Tag 객체)
        
    Returns:
        클릭 가능한 요소만 필터링된 리스트 (중복 제거됨)
    """
    filtered = []
    seen = set()  # 중복 제거를 위한 set
    
    for tag in candidates:
        # 중복 체크 (같은 태그 객체는 한 번만 추가)
        tag_id = id(tag)
        if tag_id in seen:
            continue 
        seen.add(tag_id)
        
        # 1) <a> 태그 자체면 100% 클릭 가능
        if tag.name == "a":
            filtered.append(tag)
            continue
        
        # 2) tag 내부에 <a> 가 있으면 클릭 가능
        if tag.find("a"):
            filtered.append(tag)
            continue
        
        # 3) onclick 속성 존재 → JavaScript 로 클릭 처리하는 메뉴
        if tag.get("onclick"):
            filtered.append(tag)
            continue
        
        # 4) role="button" 또는 class 에 "btn" 포함
        class_list = tag.get("class", [])
        class_str = " ".join(class_list).lower()
        if tag.get("role") == "button" or "btn" in class_str:
            filtered.append(tag)
            continue
        
        # 5) 스타일에 cursor:pointer 포함 → 클릭 가능한 요소
        # 개선: 대소문자 무시, 다양한 형식 지원 (cursor:pointer, cursor: pointer 등)
        style = tag.get("style", "")
        if style:
            # 소문자로 변환하고 다양한 형식 지원
            style_lower = style.lower()
            # cursor:pointer, cursor: pointer, cursor:pointer; 등 다양한 형식 매칭
            if "cursor:pointer" in style_lower or "cursor: pointer" in style_lower:
                filtered.append(tag)
                continue
    
    return filtered


def detect_hover_needed(tag: Tag) -> bool:
    """
    정적 분석 기반으로 dropdown / hover 기반 메뉴인지 감지.
    완전 정확하진 않지만, 패턴 분석으로 70~90% 탐지 가능.
    
    Args:
        tag: BeautifulSoup Tag 객체
        
    Returns:
        hover가 필요한 요소인지 여부 (bool)
    """
    class_list = tag.get("class", [])
    class_str = " ".join(class_list).lower()
    
    # 1) class 이름에 submenu/dropdown/hover 관련 존재
    hover_keywords = [
        "submenu", "sub-menu", "dropdown", "drop-menu",
        "has-submenu", "hover", "hover-open", "depth1", "depth2",
        "mega-menu", "mega-menu", "flyout", "fly-out",
        "has-children", "has-child", "parent",
        "level-2", "level2", "l2", "l3"
    ]
    if any(keyword in class_str for keyword in hover_keywords):
        return True
    
    # 2) CSS 클래스로 숨겨진 요소 체크
    hidden_classes = ["hidden", "d-none", "invisible", "collapse", "visually-hidden"]
    if any(cls in class_str for cls in hidden_classes):
        # 숨겨진 클래스가 있고 내부에 메뉴 구조가 있으면 hover 가능성
        if tag.find(["ul", "div"], recursive=True):
            return True
    
    # 3) tag 내부에 숨겨진 <ul> or <div> 존재 (다양한 숨김 방식 체크)
    for child in tag.find_all(["ul", "div"], recursive=True, limit=5):  # 성능 최적화
        style = child.get("style", "").replace(" ", "").lower()
        hidden_patterns = [
            "display:none", "visibility:hidden", "opacity:0",
            "height:0", "max-height:0", "width:0", "max-width:0"
        ]
        if any(pattern in style for pattern in hidden_patterns):
            return True
    
    # 4) aria-haspopup / aria-expanded 속성 패턴
    if tag.get("aria-haspopup") == "true":
        return True
    
    # aria-expanded가 존재하면 hover 가능성 (true/false 모두)
    if tag.get("aria-expanded") is not None:
        return True
    
    # 5) data 속성 체크
    if tag.get("data-toggle") == "dropdown" or tag.get("data-hover") == "true":
        return True
    
    # 6) role 속성 체크
    role = tag.get("role", "").lower()
    if role in ["menu", "menuitem"]:
        return True
    
    # 7) onclick이 없고, 내부에 submenu가 존재하면 hover일 가능성↑
    if not tag.get("onclick"):
        # <ul> 또는 <div> 내부에 여러 메뉴 항목이 있으면 hover 가능성
        submenu_containers = tag.find_all(["ul", "div"], recursive=True, limit=3)
        if len(submenu_containers) >= 1:
            # 내부에 <li> 또는 <a>가 여러 개 있으면 submenu일 가능성
            menu_items = tag.find_all(["li", "a"], recursive=True, limit=5)
            if len(menu_items) >= 2:  # 최소 2개 이상의 메뉴 항목
                return True
    
    return False
