"""
淘宝/天猫竞品负面评价抓取 (始祖鸟、萨洛蒙、巴塔哥尼亚等机能风品牌)
使用 justoneapi SDK: pip install justoneapi
用法: python taobao_review_scraper.py --token YOUR_TOKEN [--max-products N] [--output FILE]
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

# 只保留差评/中评（1-2星），score=0 表示接口未返回分数，全部保留
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


_FIRST_ITEM_DUMPED = False
_FIRST_COMMENT_DUMPED = False


def search_products(client: JustOneAPIClient, keyword: str, max_n: int) -> list[dict]:
    global _FIRST_ITEM_DUMPED
    try:
        resp = client.taobao.search_item_list_v1(keyword=keyword, sort="_sale")
    except Exception as e:
        print(f"  搜索异常: {e}")
        return []

    if not resp.success:
        print(f"  搜索失败: {resp.message}")
        return []

    data = resp.data or {}
    model = data.get("model") or {}
    items = (
        model.get("itemList")
        or model.get("items")
        or model.get("itemsArray")
        or data.get("items")
        or (data if isinstance(data, list) else [])
    )
    if items and not _FIRST_ITEM_DUMPED:
        _FIRST_ITEM_DUMPED = True
        print(f"  [DEBUG] 首个商品字段: {json.dumps(items[0], ensure_ascii=False)[:800]}")
    if not items:
        print(f"  [DEBUG] data keys={list(data.keys())}, model keys={list(model.keys())}")
    return items[:max_n]


def fetch_comments(client: JustOneAPIClient, item_id: str, max_pages: int) -> list[dict]:
    global _FIRST_COMMENT_DUMPED
    comments = []
    for page in range(1, max_pages + 1):
        # 重试 COLLECT FAILED 这类瞬时错误
        resp = None
        for attempt in range(3):
            try:
                resp = client.taobao.get_item_comment_v3(
                    item_id=item_id,
                    page=page,
                    order_type="feedbackdate",
                )
            except Exception as e:
                print(f"    评论异常 (page={page}, try={attempt+1}): {e}")
                time.sleep(1.5 * (attempt + 1))
                continue

            if resp.success:
                break
            msg = (resp.message or "").upper()
            if "COLLECT FAILED" in msg or "RATE" in msg or "TIMEOUT" in msg:
                time.sleep(1.5 * (attempt + 1))
                continue
            break

        if not resp or not resp.success:
            print(f"    评论API错误 (page={page}): {resp.message if resp else 'no response'}")
            break

        data = resp.data or {}
        model = data.get("model") or {}
        raw_list = (
            model.get("commentList")
            or model.get("comments")
            or model.get("reviews")
            or model.get("list")
            or data.get("comments")
            or data.get("list")
            or (data if isinstance(data, list) else [])
        )
        if not raw_list:
            if page == 1:
                print(f"    [DEBUG] data keys={list(data.keys())}, model keys={list(model.keys())}")
                print(f"    [DEBUG] full: {json.dumps(data, ensure_ascii=False)[:600]}")
            break

        if not _FIRST_COMMENT_DUMPED:
            _FIRST_COMMENT_DUMPED = True
            print(f"    [DEBUG] 首条评论字段: {json.dumps(raw_list[0], ensure_ascii=False)[:800]}")

        comments.extend(raw_list)
        time.sleep(0.5)

    return comments


def scrape_taobao(
    token: str,
    output_path: Path,
    max_products_per_query: int,
    max_review_pages: int,
) -> None:
    client = JustOneAPIClient(token=token)
    records: list[ReviewRecord] = []

    for query in COMPETITOR_QUERIES:
        print(f"\n搜索淘宝/天猫: {query}")
        products = search_products(client, query, max_products_per_query)
        print(f"  找到 {len(products)} 个商品")

        for item in products:
            item_id = get_nested(
                item, "itemId", "item_id", "numIid", "num_iid",
                "product_id", "id",
            )
            name = get_nested(
                item, "itemTitle", "title", "subject", "displayTitle",
                "name", "product_name", "item_title",
            )
            if not item_id:
                continue
            print(f"  商品 {item_id}: {name[:35]}")

            raw_comments = fetch_comments(client, item_id, max_review_pages)
            saved = 0
            for raw in raw_comments:
                score_val = (
                    raw.get("rateStar") or raw.get("star") or raw.get("score")
                    or raw.get("rating") or raw.get("rate") or 0
                )
                try:
                    score = int(score_val)
                except (TypeError, ValueError):
                    score = 0
                content = (
                    raw.get("feedback") or raw.get("rateContent") or raw.get("content")
                    or raw.get("text") or raw.get("comment") or raw.get("rate_content")
                    or ""
                ).strip()
                if not content:
                    continue
                # 本地过滤差评/中评；score=0 说明接口未返回分数，全部保留
                if score and score not in NEGATIVE_SCORES:
                    continue
                records.append(ReviewRecord(
                    platform="taobao",
                    query=query,
                    product_id=item_id,
                    product_name=name,
                    score=score,
                    content=content,
                    creation_time=get_nested(
                        raw, "creationTime", "create_time", "date", "created"
                    ),
                    product_color=get_nested(raw, "productColor", "color", "sku_color"),
                    product_size=get_nested(raw, "productSize", "size", "sku_size"),
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
    parser = argparse.ArgumentParser(description="用 justoneapi 抓取淘宝/天猫竞品评价")
    parser.add_argument("--token", required=True, help="justoneapi token（在官网注册后获取）")
    parser.add_argument("--max-products", type=int, default=5)
    parser.add_argument("--max-review-pages", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("taobao_reviews.json"))
    args = parser.parse_args()

    scrape_taobao(args.token, args.output, args.max_products, args.max_review_pages)


if __name__ == "__main__":
    main()
