"""
Dataclasses representing RabbitMQ payloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BlogUploadRequest:
    work_id: Optional[int]
    blog_type: str
    title: Optional[str]
    content: Optional[str]
    blog_id: str
    blog_password: str
    blog_url: str
    webhook_url: Optional[str] = None
    webhook_token: Optional[str] = None
    is_test: bool = False

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BlogUploadRequest":
        return cls(
            work_id=payload.get("workId"),
            blog_type=(payload.get("blogType") or "").lower(),
            title=payload.get("title"),
            content=payload.get("content"),
            blog_id=payload.get("blogId") or "",
            blog_password=payload.get("blogPassword") or "",
            blog_url=payload.get("blogUrl") or "",
            webhook_url=payload.get("webhookUrl"),
            webhook_token=payload.get("webhookToken"),
            is_test=bool(payload.get("isTest")),
        )

    @classmethod
    def from_json(cls, raw: bytes | str) -> "BlogUploadRequest":
        data = json.loads(raw)
        return cls.from_dict(data)
