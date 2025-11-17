"""
파일 관리 유틸리티
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class FileManager:
    """파일 저장 및 로드 관리 클래스"""
    
    def __init__(self, base_dir: str = "data"):
        """
        Args:
            base_dir: 기본 데이터 디렉토리
        """
        self.base_dir = Path(__file__).parent.parent / base_dir
        self.base_dir.mkdir(exist_ok=True)
    
    def save_json(self, data: Dict[Any, Any], filename: str, subdir: str = "") -> Path:
        """
        JSON 파일로 데이터를 저장합니다.
        
        Args:
            data: 저장할 데이터 (딕셔너리)
            filename: 파일명 (확장자 포함)
            subdir: 하위 디렉토리
            
        Returns:
            저장된 파일 경로
        """
        if subdir:
            save_dir = self.base_dir / subdir
        else:
            save_dir = self.base_dir
        
        save_dir.mkdir(exist_ok=True)
        file_path = save_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def load_json(self, filename: str, subdir: str = "") -> Optional[Dict[Any, Any]]:
        """
        JSON 파일에서 데이터를 로드합니다.
        
        Args:
            filename: 파일명
            subdir: 하위 디렉토리
            
        Returns:
            로드된 데이터 (딕셔너리) 또는 None
        """
        if subdir:
            load_dir = self.base_dir / subdir
        else:
            load_dir = self.base_dir
        
        file_path = load_dir / filename
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_html(self, content: str, filename: str, subdir: str = "") -> Path:
        """
        HTML 파일로 콘텐츠를 저장합니다.
        
        Args:
            content: HTML 콘텐츠
            filename: 파일명
            subdir: 하위 디렉토리
            
        Returns:
            저장된 파일 경로
        """
        if subdir:
            save_dir = self.base_dir / subdir
        else:
            save_dir = self.base_dir
        
        save_dir.mkdir(exist_ok=True)
        file_path = save_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def generate_filename(self, prefix: str, extension: str = "json") -> str:
        """
        타임스탬프 기반 파일명을 생성합니다.
        
        Args:
            prefix: 파일명 접두사
            extension: 파일 확장자
            
        Returns:
            생성된 파일명
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}.{extension}"

