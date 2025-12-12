import json

# JSON 파일 로드
with open("itemscout_all_categories.json", "r", encoding="utf-8") as f:
    data = json.load(f)

insert_queries = []


def process_category(cat, parent_id=None):
    """
    cat: dict, {"id": ..., "name": ..., "depth": ..., "children": [...]}
    parent_id: 부모 카테고리 id (없으면 None)
    """
    cid = cat["id"]
    name = cat["name"].replace("'", "''")  # SQL 문자열 이스케이프
    depth = cat["depth"]

    # INSERT 쿼리 생성
    query = f"""
    INSERT INTO trend_category (trend_category_id, parent_category_id, trend_category_name, depth)
    VALUES ({cid}, {parent_id if parent_id else 'NULL'}, '{name}', {depth});
    """
    insert_queries.append(query.strip())

    # 자식 카테고리 재귀 처리
    for child in cat.get("children", []):
        process_category(child, cid)


# 최상위 카테고리부터 처리
for top_cat in data:
    process_category(top_cat)

# SQL 파일 저장
with open("trend_category_inserts.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(insert_queries))

print(f"총 {len(insert_queries)}개의 INSERT 쿼리 생성됨 → trend_category_inserts.sql")
