import json
import time
from playwright.sync_api import sync_playwright

API_PREFIX = "https://api.itemscout.io/api/category/"
RESULT = []


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        page = browser.new_page()

        api_storage = []

        # 모든 response 이벤트 감지
        def handle_response(response):
            url = response.url
            if "/subcategories" in url and API_PREFIX in url:
                try:
                    data = response.json()
                    api_storage.append((url, data))
                except:
                    pass

        page.on("response", handle_response)

        # 0번 페이지 → 1차 카테고리 데이터 가져오기
        page.goto("https://itemscout.io/category/0", wait_until="networkidle")
        time.sleep(1)
        resp = page.request.get(f"{API_PREFIX}0/subcategories").json()
        first_level_categories = resp["data"]

        for cat1 in first_level_categories:
            cat1_id = cat1["id"]
            cat1_node = {
                "id": cat1_id,
                "name": cat1["name"],
                "depth": 1,
                "children": [],
            }

            print(f"➡ 1차 카테고리 이동: {cat1['name']} ({cat1_id})")
            page.goto(
                f"https://itemscout.io/category/{cat1_id}", wait_until="networkidle"
            )
            time.sleep(0.5)

            # 2차 카테고리 데이터 수집
            two_level_categories = []
            for url, data in api_storage:
                if f"/category/{cat1_id}/subcategories" in url:
                    for item in data["data"]:
                        two_level_categories.append(
                            {
                                "id": item["id"],
                                "name": item["name"],
                                "depth": 2,
                                "children": [],
                            }
                        )

            # 2차 카테고리 URL 방문 → 3차 데이터 수집
            for cat2 in two_level_categories:
                cat2_id = cat2["id"]
                print(f"    ↳ 2차 카테고리 이동: {cat2['name']} ({cat2_id})")
                page.goto(
                    f"https://itemscout.io/category/{cat2_id}",
                    wait_until="networkidle",
                    timeout=60000,
                )
                time.sleep(0.5)

                # 3차 카테고리 수집
                for url, data in api_storage:
                    if f"/category/{cat2_id}/subcategories" in url:
                        for item in data["data"]:
                            cat2["children"].append(
                                {
                                    "id": item["id"],
                                    "name": item["name"],
                                    "depth": 3,
                                    "children": [],  # 4차 이상은 수집하지 않음
                                }
                            )

            # 1차 카테고리 하위에 2차 카테고리 붙이기
            cat1_node["children"] = two_level_categories
            RESULT.append(cat1_node)

        # JSON 저장
        with open("itemscout_all_categories.json", "w", encoding="utf-8") as f:
            json.dump(RESULT, f, ensure_ascii=False, indent=2)

        print("🎉 1~3차 카테고리 모두 수집 완료")
        browser.close()


if __name__ == "__main__":
    main()
