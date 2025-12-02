"""
카테고리 트리 구조 정의
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class CategoryNode:
    """
    카테고리 노드 클래스
    트리 구조로 카테고리 계층을 표현
    """
    name: str
    category_id: Optional[str] = None
    url: Optional[str] = None
    xpath: Optional[str] = None
    node_type: str = "unknown"  # root, main, sub, leaf
    depth: int = 0
    children: List['CategoryNode'] = field(default_factory=list)
    parent: Optional['CategoryNode'] = None
    
    def add_child(self, child: 'CategoryNode'):
        """하위 카테고리 추가"""
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)
    
    def get_path(self) -> List[str]:
        """루트부터 현재 노드까지의 경로 반환"""
        path = []
        node = self
        while node:
            if node.name != "root":
                path.insert(0, node.name)
            node = node.parent
        return path
    
    def find_by_path(self, path: List[str]) -> Optional['CategoryNode']:
        """경로로 카테고리 노드 찾기"""
        if not path:
            return self
        
        target_name = path[0]
        for child in self.children:
            if child.name == target_name:
                if len(path) == 1:
                    return child
                return child.find_by_path(path[1:])
        
        return None
    
    def is_leaf(self) -> bool:
        """리프 노드인지 확인"""
        return len(self.children) == 0
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "category_id": self.category_id,
            "url": self.url,
            "xpath": self.xpath,
            "node_type": self.node_type,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children]
        }
    
    def __repr__(self):
        return f"CategoryNode(name='{self.name}', depth={self.depth}, children={len(self.children)})"


class CategoryTree:
    """
    카테고리 트리 관리 클래스
    """
    def __init__(self):
        self.root = CategoryNode("root", node_type="root")
        self._node_map: Dict[str, CategoryNode] = {}
    
    def add_category(self, path: List[str], category_id: Optional[str] = None, url: Optional[str] = None):
        """카테고리 경로 추가"""
        current = self.root
        
        for i, name in enumerate(path):
            # 이미 존재하는 노드 찾기
            found = None
            for child in current.children:
                if child.name == name:
                    found = child
                    break
            
            if not found:
                # 새 노드 생성
                found = CategoryNode(
                    name=name,
                    node_type="main" if i == 0 else "sub",
                    depth=i + 1
                )
                current.add_child(found)
            
            current = found
        
        # 마지막 노드에 정보 추가
        if category_id:
            current.category_id = category_id
        if url:
            current.url = url
        current.node_type = "leaf"
    
    def find_by_path(self, path: List[str]) -> Optional[CategoryNode]:
        """경로로 카테고리 찾기"""
        return self.root.find_by_path(path)
    
    def get_all_paths(self) -> List[List[str]]:
        """모든 카테고리 경로 반환"""
        paths = []
        
        def traverse(node: CategoryNode, current_path: List[str]):
            if node.name != "root":
                current_path.append(node.name)
                if not node.children:  # 리프 노드
                    paths.append(current_path.copy())
            
            for child in node.children:
                traverse(child, current_path.copy())
        
        traverse(self.root, [])
        return paths
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return self.root.to_dict()
