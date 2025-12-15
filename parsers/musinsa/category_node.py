@dataclass
class CategoryNode:
    name: str
    url: Optional[str] = None
    xpath: Optional[str] = None
    children: List["CategoryNode"] = field(default_factory=list)
    parent: Optional["CategoryNode"] = None  # 추가 고려
    
    def add_child(self, child: "CategoryNode"):
        child.parent = self
        self.children.append(child)
    
    def is_leaf(self) -> bool:
        return len(self.children) == 0
    
    def get_path(self) -> List[str]:  # 추가 고려
        """루트부터 현재 노드까지의 경로"""
        path = []
        node = self
        while node and node.name != "root":
            path.insert(0, node.name)
            node = node.parent
        return path