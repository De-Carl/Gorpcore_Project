"""
Bilibili 机能风评测视频 弹幕 + 高赞评论 抓取
用法: python bilibili_scraper.py [--max-videos N] [--output FILE]
"""
import argparse
import asyncio
import gzip
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth

_stealth = Stealth()

SEARCH_KEYWORDS = ["机能风", "Gorpcore"]

PAIN_POINT_KEYWORDS = [
    "太热", "太重", "不日常", "不实用", "闷热", "笨重", "贵",
    "性价比", "不耐用", "穿不出去", "显胖", "不好搭", "买亏了",
    "后悔", "退款", "差评", "质量差", "起球",
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class DanmakuRecord:
    keyword: str
    bvid: str
    video_title: str
    text: str
    is_pain_point: bool


@dataclass
class CommentRecord:
    keyword: str
    bvid: str
    video_title: str
    text: str
    like_count: int
    is_pain_point: bool


def contains_pain_point(text: str) -> bool:
    return any(kw in text for kw in PAIN_POINT_KEYWORDS)


def parse_danmaku_bytes(content: bytes) -> list[str]:
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    content = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", content)
    try:
        root = ET.fromstring(content)
        return [d.text.strip() for d in root.findall("d") if d.text]
    except ET.ParseError as e:
        print(f"    XML解析失败: {e} | 前50字节: {content[:50]}")
        return []


async def fetch_danmaku(page: Page, cid: int) -> list[str]:
    """用浏览器内的 JS fetch 拉弹幕 XML，Chrome 自行处理 SSL 和解压。"""
    url = f"https://comment.bilibili.com/{cid}.xml"
    xml_text = await page.evaluate(
        """async (url) => {
            try {
                const r = await fetch(url, {credentials: 'include'});
                return r.ok ? await r.text() : null;
            } catch(e) { return null; }
        }""",
        url,
    )
    if not xml_text:
        return []
    try:
        content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", xml_text).encode()
        root = ET.fromstring(content)
        return [d.text.strip() for d in root.findall("d") if d.text]
    except ET.ParseError as e:
        print(f"    XML解析失败: {e}")
        return []


async def fetch_top_comments(page: Page, aid: int, max_pages: int) -> list[dict]:
    comments = []
    seen: set[str] = set()

    def collect(entries: list) -> None:
        for r in entries or []:
            text = (r.get("content") or {}).get("message", "")
            rpid = str(r.get("rpid", ""))
            if text and rpid not in seen:
                seen.add(rpid)
                comments.append({"text": text, "like": r.get("like", 0)})

    async def bili_fetch(url: str) -> dict | None:
        return await page.evaluate(
            """async (url) => {
                try {
                    const r = await fetch(url, {credentials: 'include'});
                    return r.ok ? await r.json() : null;
                } catch(e) { return null; }
            }""",
            url,
        )

    # 第一步：mode=3 取热评和置顶，游标不跨模式复用
    url = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={aid}&mode=3&ps=20&pn=1"
    data = await bili_fetch(url)
    if data:
        d = data.get("data") or {}
        collect(d.get("top_replies") or [])
        collect(d.get("hots") or [])
        collect(d.get("replies") or [])
    await asyncio.sleep(0.6)

    # 第二步：mode=2 从头独立翻页，用 cursor.next 推进，cursor.is_end 终止
    next_cursor: int | None = None  # None = 第一页不带 next 参数
    for _ in range(max_pages):
        if next_cursor is None:
            url = f"https://api.bilibili.com/x/v2/reply/main?type=1&oid={aid}&mode=2&ps=20"
        else:
            url = (
                f"https://api.bilibili.com/x/v2/reply/main"
                f"?type=1&oid={aid}&mode=2&ps=20&next={next_cursor}"
            )
        data = await bili_fetch(url)
        if not data:
            break
        d = data.get("data") or {}
        replies = d.get("replies") or []
        collect(replies)
        cursor = d.get("cursor") or {}
        if cursor.get("is_end") or not replies:
            break
        next_cursor = cursor.get("next")
        if not next_cursor:
            break
        await asyncio.sleep(0.6)

    return comments


async def get_video_info(page: Page, bvid: str) -> dict | None:
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    data = await page.evaluate(
        """async (url) => {
            try {
                const r = await fetch(url, {credentials: 'include'});
                return r.ok ? await r.json() : null;
            } catch(e) { return null; }
        }""",
        url,
    )
    if not data:
        print(f"    获取视频信息失败 ({bvid})")
        return None
    vd = data.get("data") or {}
    pages = vd.get("pages") or []
    cid = pages[0].get("cid") if pages else None
    aid = vd.get("aid")
    return {"aid": aid, "cid": cid} if aid and cid else None


async def search_videos_via_page(page: Page, keyword: str, max_videos: int) -> list[dict]:
    url = f"https://search.bilibili.com/video?keyword={quote(keyword)}&order=dm"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
    except Exception as e:
        print(f"  搜索页面加载失败 ({keyword}): {e}")
        return []

    for _ in range(3):
        await page.evaluate("window.scrollBy(0, 900)")
        await page.wait_for_timeout(800)

    items = await page.evaluate("""
        () => {
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a[href*="/video/BV"]').forEach(a => {
                const m = a.href.match(/\\/video\\/(BV[\\w]+)/);
                if (!m) return;
                const bvid = m[1];
                if (seen.has(bvid)) return;
                seen.add(bvid);
                let title = '';
                const card = a.closest('.bili-video-card');
                const titleEl = card && card.querySelector('.bili-video-card__info--tit');
                title = titleEl ? titleEl.innerText.trim() : a.innerText.trim().slice(0, 80);
                if (bvid.length > 5) results.push({ bvid, title });
            });
            return results;
        }
    """)
    videos = (items or [])[:max_videos]
    print(f"  从搜索页找到 {len(videos)} 个视频")
    return videos


async def scrape_bilibili(
    output_path: Path,
    max_videos_per_keyword: int,
    max_comment_pages: int,
    headless: bool,
) -> None:
    danmaku_records: list[DanmakuRecord] = []
    comment_records: list[CommentRecord] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=UA,
            locale="zh-CN",
        )
        page = await ctx.new_page()
        await _stealth.apply_stealth_async(page)

        print("正在打开Bilibili...")
        await page.goto("https://www.bilibili.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)
        await asyncio.to_thread(input, "请在浏览器中完成B站登录，登录后按回车开始抓取... ")

        for keyword in SEARCH_KEYWORDS:
            print(f"\n搜索关键词: {keyword}")
            videos = await search_videos_via_page(page, keyword, max_videos_per_keyword)

            for video in videos:
                bvid = video["bvid"]
                title = video["title"] or bvid
                print(f"  处理: [{bvid}] {title[:40]}")

                info = await get_video_info(page, bvid)
                if not info:
                    continue
                cid, aid = info["cid"], info["aid"]

                # 弹幕
                try:
                    texts = await fetch_danmaku(page, cid)
                    for text in texts:
                        danmaku_records.append(DanmakuRecord(
                            keyword=keyword, bvid=bvid, video_title=title,
                            text=text, is_pain_point=contains_pain_point(text),
                        ))
                    pain = sum(1 for t in texts if contains_pain_point(t))
                    print(f"    弹幕 {len(texts)} 条 (含痛点 {pain} 条)")
                except Exception as e:
                    print(f"    弹幕获取失败: {e}")
                await asyncio.sleep(0.5)

                # 评论
                try:
                    raw_comments = await fetch_top_comments(page, aid, max_comment_pages)
                    for c in raw_comments:
                        comment_records.append(CommentRecord(
                            keyword=keyword, bvid=bvid, video_title=title,
                            text=c["text"], like_count=c["like"],
                            is_pain_point=contains_pain_point(c["text"]),
                        ))
                    pain = sum(1 for c in raw_comments if contains_pain_point(c["text"]))
                    print(f"    评论 {len(raw_comments)} 条 (含痛点 {pain} 条)")
                except Exception as e:
                    print(f"    评论获取失败: {e}")
                await asyncio.sleep(1.0)

        await browser.close()

    pain_dm = [r for r in danmaku_records if r.is_pain_point]
    pain_cm = [r for r in comment_records if r.is_pain_point]
    high_like_pain = sorted(pain_cm, key=lambda x: x.like_count, reverse=True)

    result = {
        "summary": {
            "total_danmaku": len(danmaku_records),
            "pain_point_danmaku": len(pain_dm),
            "total_comments": len(comment_records),
            "pain_point_comments": len(pain_cm),
        },
        "pain_point_keywords": PAIN_POINT_KEYWORDS,
        "high_like_pain_comments": [asdict(r) for r in high_like_pain[:50]],
        "pain_point_danmaku": [asdict(r) for r in pain_dm],
        "all_danmaku": [asdict(r) for r in danmaku_records],
        "all_comments": [asdict(r) for r in comment_records],
    }

    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n完成: 弹幕 {len(danmaku_records)} 条 (痛点 {len(pain_dm)} 条)，"
          f"评论 {len(comment_records)} 条 (痛点 {len(pain_cm)} 条)")
    print(f"结果保存到: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取Bilibili机能风视频弹幕与评论")
    parser.add_argument("--max-videos", type=int, default=10)
    parser.add_argument("--max-comment-pages", type=int, default=3)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("bilibili_results.json"))
    args = parser.parse_args()

    asyncio.run(scrape_bilibili(
        args.output, args.max_videos, args.max_comment_pages, args.headless,
    ))


if __name__ == "__main__":
    main()
