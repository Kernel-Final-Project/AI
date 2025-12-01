"""
Standalone blog auto-posting package.

This package is a self-contained copy of the auto posting logic so you
can run blog uploaders without the rest of the repository.
"""

from .naver_uploader import upload_to_naver_blog  # noqa: F401
from .results import UploadResult  # noqa: F401
from .tistory_uploader import upload_to_tistory_blog  # noqa: F401
