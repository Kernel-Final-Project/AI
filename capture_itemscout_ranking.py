"""
Itemscout 키워드 분석 탭에서 상위 20개 키워드를 수집하는 간단한 스크립트.

주의:
- Itemscout는 로그인/유료 서비스이므로 약관을 준수해야 합니다.
- 페이지 구조/셀렉터는 변경될 수 있습니다. 필요 시 ROW_SELECTOR, KEYWORD_CELL, RANK_CELL을 수정하세요.
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://itemscout.io/keyword"  # 키워드 분석 탭
OUT = Path("data/itemscout_keyword_top20.json")

# 페이지 DOM 구조에 맞게 필요 시 조정
ROW_SELECTOR = "table tbody tr"
RANK_CELL = "td:nth-child(1)"
KEYWORD_CELL = "td:nth-child(2)"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)

        count = min(page.locator(ROW_SELECTOR).count(), 20)
        top20 = page.evaluate(
            """
            ({rowSelector, count}) => {
              const rows = Array.from(document.querySelectorAll(rowSelector)).slice(0, count);
              const stars = new Set(['★','☆','','☆']);
              const result = [];
              rows.forEach((row, idx) => {
                const cells = Array.from(row.querySelectorAll('td'));
                let rank = String(idx + 1); // 별 아이콘 무시하고 인덱스로 랭크 부여
                let keyword = '';
                for (const td of cells) {
                  const txt = (td.innerText || '').trim();
                  if (!txt) continue;
                  if (stars.has(txt)) continue;
                  if (/^\\d+$/.test(txt)) continue;
                  keyword = txt;
                  break;
                }
                if (keyword) result.push({rank, keyword});
              });
              return result;
            }
            """,
            {"rowSelector": ROW_SELECTOR, "count": count},
        )

        browser.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(top20, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {OUT} (rows: {len(top20)})")
    for item in top20:
        print(f"{item['rank']}: {item['keyword']}")


if __name__ == "__main__":
    main()
