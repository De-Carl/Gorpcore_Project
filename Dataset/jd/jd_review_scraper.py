"""
京东竞品负面评价抓取 (始祖鸟、萨洛蒙等机能风品牌)
使用 justoneapi SDK: pip install justoneapi
用法: python jd_review_scraper.py --token YOUR_TOKEN [--max-products N] [--output FILE]
"""
import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from justoneapi import JustOneAPIClient

COMPETITOR_QUERIES = [
    "始祖鸟 冲锋衣",
    "始祖鸟 软壳",
    "萨洛蒙 冲锋衣",
    "萨洛蒙 徒步鞋",
    "巴塔哥尼亚 冲锋衣",
    "始祖鸟 抓绒",
]

# 只保留差评/中评（1-2星），需在本地过滤（API 不支持按分数筛选）
NEGATIVE_SCORES = {1, 2}


@dataclass
class ReviewRecord:
    platform: str
    query: str
    product_id: str
    product_name: str
    score: int
    content: str
    creation_time: str
    product_color: str
    product_size: str


def get_nested(d: dict, *keys: str, default="") -> str:
    for key in keys:
        val = d.get(key)
        if val is not None:
            return str(val).strip()
    return default


def search_products(client: JustOneAPIClient, keyword: str, max_n: int) -> list[dict]:
    try:
        resp = client.jd.search_item_list_v1(keyword=keyword)
    except Exception as e:
        print(f"  搜索异常: {e}")
        return []

    if not resp.success:
        print(f"  搜索失败: {resp.message}")
        return []

    data = resp.data
    print(f"  [DEBUG] data type={type(data).__name__}, value={json.dumps(data, ensure_ascii=False)[:300]}")
    items = data if isinstance(data, list) else (data or {}).get("items") or []
    return items[:max_n]


def fetch_comments(client: JustOneAPIClient, item_id: str, max_pages: int) -> list[dict]:
    comments = []
    for page in range(max_pages):
        try:
            resp = client.jd.get_item_comments_v1(item_id=item_id, page=str(page))
        except Exception as e:
            print(f"    评论获取失败 (page={page}): {e}")
            break

        if not resp.success:
            print(f"    评论API错误: {resp.message}")
            break

        data = resp.data
        raw_list = (
            data if isinstance(data, list)
            else (data or {}).get("comments")
            or (data or {}).get("list")
            or []
        )
        if not raw_list:
            break

        comments.extend(raw_list)
        time.sleep(0.5)

    return comments


def scrape_jd(
    token: str,
    output_path: Path,
    max_products_per_query: int,
    max_review_pages: int,
) -> None:
    client = JustOneAPIClient(token=token)
    records: list[ReviewRecord] = []

    for query in COMPETITOR_QUERIES:
        print(f"\n搜索京东: {query}")
        products = search_products(client, query, max_products_per_query)
        print(f"  找到 {len(products)} 个商品")

        for item in products:
            item_id = get_nested(item, "item_id", "product_id", "skuId", "id")
            name = get_nested(item, "title", "name", "product_name", "skuName")
            if not item_id:
                continue
            print(f"  商品 {item_id}: {name[:35]}")

            raw_comments = fetch_comments(client, item_id, max_review_pages)
            saved = 0
            for raw in raw_comments:
                score_val = raw.get("score") or raw.get("star") or raw.get("rating") or 0
                score = int(score_val)
                content = (
                    raw.get("content") or raw.get("text") or raw.get("comment") or ""
                ).strip()
                if not content:
                    continue
                # 本地过滤差评/中评；若 score=0 说明接口未返回分数，全部保留
                if score and score not in NEGATIVE_SCORES:
                    continue
                records.append(ReviewRecord(
                    platform="jd",
                    query=query,
                    product_id=item_id,
                    product_name=name,
                    score=score,
                    content=content,
                    creation_time=get_nested(raw, "creationTime", "create_time", "date"),
                    product_color=get_nested(raw, "productColor", "color"),
                    product_size=get_nested(raw, "productSize", "size"),
                ))
                saved += 1
            print(f"    差/中评 {saved} 条（共拉取 {len(raw_comments)} 条）")
            time.sleep(1.0)

    by_brand: dict[str, int] = {}
    for r in records:
        brand = r.query.split()[0]
        by_brand[brand] = by_brand.get(brand, 0) + 1

    result = {
        "summary": {"total_reviews": len(records), "by_brand": by_brand},
        "reviews": [asdict(r) for r in records],
    }
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n完成: 共抓取 {len(records)} 条差/中评，保存到: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="用 justoneapi 抓取京东竞品评价")
    parser.add_argument("--token", required=True, help="justoneapi token（在官网注册后获取）")
    parser.add_argument("--max-products", type=int, default=5)
    parser.add_argument("--max-review-pages", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("jd_reviews.json"))
    args = parser.parse_args()

    scrape_jd(args.token, args.output, args.max_products, args.max_review_pages)


if __name__ == "__main__":
    main()
