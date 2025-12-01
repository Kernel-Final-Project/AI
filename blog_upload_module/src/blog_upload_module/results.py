"""
공통 업로드 결과 타입 정의.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class UploadResult:
    """
    개별 업로드 시나리오의 결과를 공통된 형태로 보관한다.
    """

    platform: str
    success: bool
    posting_url: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        return "SUCCESS" if self.success else "FAILED"

    def to_payload(self, *, work_id: Optional[str] = None) -> Dict[str, Any]:
        """
        웹훅/CLI 출력용 공통 페이로드.
        """
        payload: Dict[str, Any] = {
            "platform": self.platform,
            "success": self.success,
            "status": self.status,
            "postingUrl": self.posting_url,
            "message": self.message,
        }
        if work_id is not None:
            payload["workId"] = work_id
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload

