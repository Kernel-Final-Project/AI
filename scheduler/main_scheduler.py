# scheduler/main_scheduler.py

import sys
from pathlib import Path

# 프로젝트 루트 설정
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from content_ai.content_generator import (
    generate_title,
    generate_outline,
    generate_content,  # generate_body -> generate_content로 수정
)

if __name__ == "__main__":
    keyword = "요가매트"
    product_info = "싸다구 프리미엄 요가매트"

    title = generate_title(keyword)
    outline = generate_outline(keyword)
    content = generate_content(keyword, outline, product_info)

    print("\nTITLE:\n", title)
    print("\nOUTLINE:\n", outline)
    print("\nCONTENT:\n", content)
