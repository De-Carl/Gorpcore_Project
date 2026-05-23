import argparse
import asyncio
import calendar
import mimetypes
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen

from playwright.async_api import Error as PlaywrightError, Page, async_playwright
from playwright_stealth import Stealth
_stealth = Stealth()

SEARCH_KEYWORDS = ["#机能风穿搭", "#Gorpcore"]
SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed"
CARD_SELECTOR = 'a[href*="/explore/"], a[href*="/discovery/item/"]'
TEXT_SELECTORS = [
    "#detail-desc .note-text",
    "#detail-desc",
    "[class*='note-content']",
    "[class*='desc']",
    "article",
]
TIME_SELECTORS = [
    "time",
    "[class*='date']",
    "[class*='publish']",
    "[class*='time']",
]
IMAGE_SELECTORS = [
    "img",
    "[class*='swiper'] img",
    "[class*='media'] img",
    "[class*='note'] img",
]
SEARCH_RESPONSE_HINTS = (
    "search",
    "homefeed",
    "notefeed",
    "web/v1/",
    "sns/web/v1/",
)
DEFAULT_STORAGE_STATE = Path("xiaohongshu_auth_state.json")
DEFAULT_MIN_DELAY_SECONDS = 2.0
DEFAULT_MAX_DELAY_SECONDS = 5.0
DEFAULT_MAX_RETRIES = 3
RETRYABLE_PAGE_ERROR_HINTS = (
    "Timeout",
    "net::",
    "Navigation failed",
    "Target closed",
    "Execution context was destroyed",
)


@dataclass
class NoteRecord:
    keyword: str
    note_id: str
    note_url: str
    share_url: str | None
    xsec_token: str | None
    can_open_in_web: bool
    title_text: str | None
    raw_text: str
    text_source: str
    image_urls: list[str]
    downloaded_image_paths: list[str]
    publish_timestamp: Any
    publish_time_text: str | None = None
    publish_time_resolved: str | None = None


@dataclass
class CrawlProtection:
    min_delay_seconds: float = DEFAULT_MIN_DELAY_SECONDS
    max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES

    def __post_init__(self) -> None:
        self.min_delay_seconds = max(0.0, self.min_delay_seconds)
        self.max_delay_seconds = max(self.min_delay_seconds, self.max_delay_seconds)
        self.max_retries = max(1, self.max_retries)


async def polite_delay(
    protection: CrawlProtection, multiplier: float = 1.0, reason: str | None = None
) -> None:
    seconds = random.uniform(
        protection.min_delay_seconds, protection.max_delay_seconds
    )
    seconds *= max(0.0, multiplier)
    if reason:
        print(f"[PROTECT] {reason}，等待 {seconds:.1f}s")
    await asyncio.sleep(seconds)


def is_retryable_error(exc: Exception) -> bool:
    message = str(exc)
    return any(hint in message for hint in RETRYABLE_PAGE_ERROR_HINTS)


async def with_retry(
    label: str,
    operation,
    protection: CrawlProtection,
    retryable=None,
):
    last_error: Exception | None = None
    for attempt in range(1, protection.max_retries + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            can_retry = retryable(exc) if retryable else is_retryable_error(exc)
            if not can_retry or attempt >= protection.max_retries:
                raise
            wait_multiplier = 1.5 * attempt
            print(f"[PROTECT] {label} 第 {attempt} 次失败，准备退避重试: {exc}")
            await polite_delay(protection, multiplier=wait_multiplier)
    if last_error:
        raise last_error
    raise RuntimeError(f"{label} 未执行")


async def goto_with_retry(
    page: Page,
    label: str,
    url: str,
    wait_until: str,
    timeout: int,
    protection: CrawlProtection,
):
    try:
        return await with_retry(
            label,
            lambda: page.goto(url, wait_until=wait_until, timeout=timeout),
            protection,
        )
    except Exception as exc:
        if wait_until == "domcontentloaded" or not is_retryable_error(exc):
            raise
        print(f"[WARN] {label} 等待 {wait_until} 超时/失败，降级等待 DOM 加载继续: {exc}")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
            return None
        except Exception:
            pass
        return await with_retry(
            f"{label} DOM 加载",
            lambda: page.goto(url, wait_until="domcontentloaded", timeout=timeout),
            protection,
        )


def remove_page_listener(page: Page, event_name: str, listener) -> None:
    try:
        page.remove_listener(event_name, listener)
    except Exception:
        pass


def normalize_url(url: str) -> str:
    if not url:
        return ""
    cleaned = url.strip()
    if cleaned.startswith("data:image/"):
        return ""
    if cleaned.startswith("//"):
        cleaned = f"https:{cleaned}"
    if cleaned.startswith("/"):
        cleaned = urljoin("https://www.xiaohongshu.com", cleaned)
    return re.sub(r"\?.*$", "", cleaned)


def sanitize_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned[:80] or "untitled"


def infer_extension(url: str, content_type: str | None = None) -> str:
    lowered = url.lower()
    for extension in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"):
        if extension in lowered:
            return extension
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".jpg"


def download_image_file(url: str, destination: Path) -> str | None:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.xiaohongshu.com/",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
            extension = infer_extension(url, response.headers.get_content_type())
    except Exception:
        return None

    final_path = destination.with_suffix(extension)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(content)
    return str(final_path)


async def download_record_images(
    records: list[NoteRecord],
    download_dir: Path,
    max_images_per_note: int,
    protection: CrawlProtection | None = None,
) -> None:
    protection = protection or CrawlProtection()
    for record in records:
        downloaded_paths: list[str] = []
        note_dir_name = sanitize_filename(record.note_id or record.title_text or "note")
        keyword_dir_name = sanitize_filename(record.keyword.lstrip("#") or "keyword")
        note_dir = download_dir / keyword_dir_name / note_dir_name

        for index, image_url in enumerate(
            record.image_urls[:max_images_per_note], start=1
        ):
            file_stem = note_dir / f"image_{index:02d}"
            await polite_delay(protection, multiplier=0.35)
            downloaded = None
            for attempt in range(1, protection.max_retries + 1):
                downloaded = await asyncio.to_thread(
                    download_image_file, image_url, file_stem
                )
                if downloaded:
                    break
                if attempt < protection.max_retries:
                    await polite_delay(protection, multiplier=attempt)
            if downloaded:
                downloaded_paths.append(downloaded)

        record.downloaded_image_paths = downloaded_paths


def is_note_url(url: str) -> bool:
    return "/explore/" in url or "/discovery/item/" in url


def deep_iter(obj: Any):
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from deep_iter(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from deep_iter(value)


def extract_urls_from_obj(obj: Any) -> list[str]:
    urls: list[str] = []
    for item in deep_iter(obj):
        if isinstance(item, str) and item.startswith(("http://", "https://", "//")):
            normalized = normalize_url(item)
            lowered = normalized.lower()
            is_probably_image = any(
                token in lowered
                for token in (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".heic",
                    "xhscdn.com",
                    "imageview2",
                    "!nc_n_",
                )
            )
            if normalized and "avatar" not in lowered and is_probably_image:
                urls.append(normalized)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def normalize_timestamp(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return value


def parse_publish_time_text(text: str | None) -> int | None:
    if not text:
        return None

    value = text.strip()
    now = datetime.now()

    absolute_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", value)
    if absolute_match:
        year, month, day = map(int, absolute_match.groups())
        return calendar.timegm(datetime(year, month, day).timetuple())

    month_day_match = re.fullmatch(r"(\d{2})-(\d{2})", value)
    if month_day_match:
        month, day = map(int, month_day_match.groups())
        candidate = datetime(now.year, month, day)
        if candidate > now + timedelta(days=1):
            candidate = datetime(now.year - 1, month, day)
        return calendar.timegm(candidate.timetuple())

    day_ago_match = re.fullmatch(r"(\d+)天前", value)
    if day_ago_match:
        days = int(day_ago_match.group(1))
        candidate = now - timedelta(days=days)
        return calendar.timegm(candidate.timetuple())

    hour_ago_match = re.fullmatch(r"(\d+)小时前", value)
    if hour_ago_match:
        hours = int(hour_ago_match.group(1))
        candidate = now - timedelta(hours=hours)
        return calendar.timegm(candidate.timetuple())

    minute_ago_match = re.fullmatch(r"(\d+)分钟前", value)
    if minute_ago_match:
        minutes = int(minute_ago_match.group(1))
        candidate = now - timedelta(minutes=minutes)
        return calendar.timegm(candidate.timetuple())

    if value == "刚刚":
        return calendar.timegm(now.timetuple())

    return None


def resolve_publish_time_text(text: str | None, timestamp: int | None) -> str | None:
    if not text:
        return None

    value = text.strip()
    if not value:
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value

    if re.fullmatch(r"\d{2}-\d{2}", value) and timestamp is not None:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

    if re.fullmatch(r"\d+天前", value) and timestamp is not None:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

    if re.fullmatch(r"\d+小时前", value) and timestamp is not None:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:00")

    if re.fullmatch(r"\d+分钟前", value) and timestamp is not None:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

    if value == "刚刚" and timestamp is not None:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

    return value


def first_non_empty_str(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def first_present_value(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def derive_note_url(item: dict[str, Any]) -> str:
    direct_url = first_non_empty_str(item, ("note_url", "url", "share_url"))
    if is_note_url(direct_url):
        return normalize_url(direct_url)

    note_id = first_non_empty_str(item, ("note_id", "id", "item_id"))
    if note_id:
        return f"https://www.xiaohongshu.com/explore/{note_id}"
    return ""


def derive_note_id(item: dict[str, Any]) -> str:
    return first_non_empty_str(item, ("note_id", "id", "item_id"))


def derive_xsec_token(item: dict[str, Any], source: dict[str, Any]) -> str | None:
    token = first_non_empty_str(item, ("xsec_token",)) or first_non_empty_str(
        source, ("xsec_token",)
    )
    return token or None


def build_share_url(note_id: str, xsec_token: str | None) -> str | None:
    if not note_id or not xsec_token:
        return None
    query = urlencode({"xsec_token": xsec_token, "xsec_source": "pc_search"})
    return f"https://www.xiaohongshu.com/explore/{note_id}?{query}"


def prefer_accessible_note_url(note_url: str, share_url: str | None) -> str:
    return share_url or note_url


def can_open_in_web(share_url: str | None, xsec_token: str | None) -> bool:
    return bool(share_url and xsec_token)


def is_preview_image(url: str) -> bool:
    lowered = url.lower()
    return "_prv" in lowered or "wb_prv" in lowered


def extract_note_images(item: dict[str, Any]) -> list[str]:
    image_urls: list[str] = []

    cover = item.get("cover")
    if isinstance(cover, dict):
        for key in ("url_default", "url"):
            normalized = normalize_url(str(cover.get(key) or ""))
            if (
                normalized
                and normalized not in image_urls
                and "avatar" not in normalized.lower()
                and not is_preview_image(normalized)
            ):
                image_urls.append(normalized)

    image_list = item.get("image_list")
    if isinstance(image_list, list):
        for image in image_list:
            if not isinstance(image, dict):
                continue
            info_list = image.get("info_list")
            if isinstance(info_list, list):
                selected_url = ""
                for info in info_list:
                    if not isinstance(info, dict):
                        continue
                    normalized = normalize_url(str(info.get("url") or ""))
                    if (
                        not normalized
                        or "avatar" in normalized.lower()
                        or is_preview_image(normalized)
                    ):
                        continue
                    if info.get("image_scene") == "WB_DFT":
                        selected_url = normalized
                        break
                    if not selected_url:
                        selected_url = normalized
                if selected_url and selected_url not in image_urls:
                    image_urls.append(selected_url)

    for key in (
        "images",
        "images_list",
        "imageList",
        "img_list",
        "media",
        "cover_info",
    ):
        value = item.get(key)
        if not value:
            continue
        for url in extract_urls_from_obj(value):
            if not is_preview_image(url) and url not in image_urls:
                image_urls.append(url)

    return image_urls


def extract_publish_time_text(item: dict[str, Any]) -> str:
    corner_tag_info = item.get("corner_tag_info")
    if isinstance(corner_tag_info, list):
        for tag in corner_tag_info:
            if not isinstance(tag, dict):
                continue
            if tag.get("type") == "publish_time":
                text = str(tag.get("text") or "").strip()
                if text:
                    return text
    return first_non_empty_str(
        item,
        ("publish_time_text", "time_text", "publish_date", "date"),
    )


def should_enrich_text_from_detail(record: NoteRecord) -> bool:
    if not record.can_open_in_web or not record.share_url:
        return False
    if not record.raw_text:
        return True
    if record.title_text and record.raw_text.strip() == record.title_text.strip():
        return True
    return len(record.raw_text.strip()) <= 24


def looks_like_search_note(item: dict[str, Any]) -> bool:
    note_id = first_non_empty_str(item, ("note_id", "id", "item_id"))
    text = first_non_empty_str(
        item,
        ("desc", "content", "note_content", "display_title", "title"),
    )
    timestamp = first_present_value(
        item,
        ("publish_time", "time", "timestamp", "last_update_time", "create_time"),
    )
    has_images = bool(extract_note_images(item))
    has_card = isinstance(item.get("note_card"), dict)
    return bool(note_id) and (
        bool(text) or timestamp is not None or has_images or has_card
    )


def build_note_record_from_item(
    keyword: str, item: dict[str, Any]
) -> NoteRecord | None:
    source = item.get("note_card") if isinstance(item.get("note_card"), dict) else item
    if not isinstance(source, dict):
        source = item

    note_id = derive_note_id(item) or derive_note_id(source)
    note_url = derive_note_url(item) or derive_note_url(source)
    if not note_url or not note_id:
        return None
    xsec_token = derive_xsec_token(item, source)
    share_url = build_share_url(note_id, xsec_token)
    note_url = prefer_accessible_note_url(note_url, share_url)
    title_text = first_non_empty_str(source, ("display_title", "title")) or None

    raw_text = first_non_empty_str(
        source,
        ("desc", "content", "note_content"),
    )
    if not raw_text:
        raw_text = title_text or ""
    if raw_text == "还没有简介":
        raw_text = ""

    publish_value = first_present_value(
        source,
        ("publish_time", "time", "timestamp", "last_update_time", "create_time"),
    )
    publish_time_text = extract_publish_time_text(source) or None
    publish_timestamp = normalize_timestamp(publish_value)
    if publish_timestamp is None:
        publish_timestamp = parse_publish_time_text(publish_time_text)
    publish_time_resolved = resolve_publish_time_text(
        publish_time_text, publish_timestamp
    )
    image_urls = extract_note_images(source) or extract_note_images(item)

    if not raw_text and not image_urls and publish_timestamp is None:
        return None

    return NoteRecord(
        keyword=keyword,
        note_id=note_id,
        note_url=note_url,
        share_url=share_url,
        xsec_token=xsec_token,
        can_open_in_web=can_open_in_web(share_url, xsec_token),
        title_text=title_text,
        raw_text=raw_text,
        text_source=(
            "search_body"
            if raw_text and raw_text != (title_text or "")
            else "search_title"
        ),
        image_urls=image_urls,
        downloaded_image_paths=[],
        publish_timestamp=publish_timestamp,
        publish_time_text=publish_time_text,
        publish_time_resolved=publish_time_resolved,
    )


def parse_search_results_from_payloads(
    payloads: list[dict[str, Any]], keyword: str
) -> list[NoteRecord]:
    records_by_id: dict[str, NoteRecord] = {}

    for payload in payloads:
        for item in deep_iter(payload):
            if not isinstance(item, dict):
                continue
            if not looks_like_search_note(item):
                continue

            record = build_note_record_from_item(keyword, item)
            if not record:
                continue

            existing = records_by_id.get(record.note_id)
            if not existing:
                records_by_id[record.note_id] = record
                continue

            if not existing.raw_text and record.raw_text:
                existing.raw_text = record.raw_text
            if not existing.image_urls and record.image_urls:
                existing.image_urls = record.image_urls
            if (
                existing.publish_timestamp is None
                and record.publish_timestamp is not None
            ):
                existing.publish_timestamp = record.publish_timestamp
            if not existing.publish_time_text and record.publish_time_text:
                existing.publish_time_text = record.publish_time_text

    return list(records_by_id.values())


def merge_record(base: NoteRecord, patch: NoteRecord) -> NoteRecord:
    if not base.note_id and patch.note_id:
        base.note_id = patch.note_id
    if not base.share_url and patch.share_url:
        base.share_url = patch.share_url
    if not base.xsec_token and patch.xsec_token:
        base.xsec_token = patch.xsec_token
    if not base.can_open_in_web and patch.can_open_in_web:
        base.can_open_in_web = patch.can_open_in_web
    base.note_url = prefer_accessible_note_url(base.note_url, base.share_url)
    if not base.title_text and patch.title_text:
        base.title_text = patch.title_text
    if not base.raw_text and patch.raw_text:
        base.raw_text = patch.raw_text
    if base.text_source == "search_title" and patch.text_source != "search_title":
        base.text_source = patch.text_source
    if not base.image_urls and patch.image_urls:
        base.image_urls = patch.image_urls
    if not base.downloaded_image_paths and patch.downloaded_image_paths:
        base.downloaded_image_paths = patch.downloaded_image_paths
    if base.publish_timestamp is None and patch.publish_timestamp is not None:
        base.publish_timestamp = patch.publish_timestamp
    if not base.publish_time_text and patch.publish_time_text:
        base.publish_time_text = patch.publish_time_text
    if not base.publish_time_resolved and patch.publish_time_resolved:
        base.publish_time_resolved = patch.publish_time_resolved
    return base


def parse_note_from_payload(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for payload in payloads:
        for item in deep_iter(payload):
            if not isinstance(item, dict):
                continue
            has_text = any(
                key in item
                for key in ("desc", "content", "note_content", "display_title", "title")
            )
            has_media = any(
                key in item
                for key in ("image_list", "images", "imageList", "note_card", "media")
            )
            has_time = any(
                key in item
                for key in (
                    "time",
                    "publish_time",
                    "timestamp",
                    "last_update_time",
                    "create_time",
                )
            )
            if has_text or has_media or has_time:
                candidates.append(item)

    for item in candidates:
        raw_text = ""
        for key in ("desc", "content", "note_content", "display_title", "title"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                raw_text = value.strip()
                break

        publish_timestamp = None
        for key in (
            "publish_time",
            "time",
            "timestamp",
            "last_update_time",
            "create_time",
        ):
            value = item.get(key)
            if value is not None:
                publish_timestamp = normalize_timestamp(value)
                break

        image_urls = extract_urls_from_obj(item)
        if raw_text or image_urls or publish_timestamp is not None:
            return {
                "raw_text": raw_text,
                "image_urls": image_urls,
                "publish_timestamp": publish_timestamp,
            }

    return {"raw_text": "", "image_urls": [], "publish_timestamp": None}


async def extract_notes_from_page_state(page: Page) -> list[dict[str, Any]]:
    raw = await page.evaluate("""
        () => {
            for (const script of document.querySelectorAll('script')) {
                const t = script.textContent || '';
                if (t.includes('note_id') || t.includes('noteId') || t.includes('note_card')) {
                    return t;
                }
            }
            const s = window.__INITIAL_STATE__ || window.__pinia;
            if (s) { try { return JSON.stringify(s); } catch(e) {} }
            return null;
        }
    """)
    if not raw:
        return []
    match = re.search(r'\{.*\}|\[.*\]', raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
    except Exception:
        return []
    items: list[dict[str, Any]] = []
    for obj in deep_iter(data):
        if isinstance(obj, dict) and looks_like_search_note(obj):
            items.append(obj)
    return items


async def read_first_text(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        if await locator.count() == 0:
            continue
        text = (await locator.inner_text()).strip()
        if text:
            return text
    return ""


async def collect_dom_image_urls(page: Page) -> list[str]:
    urls: list[str] = []
    for selector in IMAGE_SELECTORS:
        locator = page.locator(selector)
        count = await locator.count()
        if count == 0:
            continue
        for index in range(min(count, 30)):
            src = await locator.nth(index).get_attribute("src")
            if not src:
                src = await locator.nth(index).get_attribute("data-src")
            normalized = normalize_url(src or "")
            if (
                normalized
                and "avatar" not in normalized.lower()
                and normalized not in urls
            ):
                urls.append(normalized)
    return urls


async def collect_note_urls(page: Page) -> list[str]:
    all_hrefs = await page.locator("a[href]").evaluate_all("""
		(elements) => elements
		  .map((element) => element.getAttribute('href') || '')
		  .filter(Boolean)
		""")
    sample = [h for h in all_hrefs if h and not h.startswith("javascript")][:20]
    print(f"[DEBUG] 页面所有链接样本({len(all_hrefs)}个): {sample}")

    hrefs = await page.locator(CARD_SELECTOR).evaluate_all("""
		(elements) => elements
		  .map((element) => element.getAttribute('href') || '')
		  .filter(Boolean)
		""")
    urls: list[str] = []
    for href in hrefs:
        normalized = normalize_url(href)
        if is_note_url(normalized) and normalized not in urls:
            urls.append(normalized)
    return urls


async def safe_page_evaluate(page: Page, expression: str) -> Any:
    for attempt in range(2):
        try:
            return await page.evaluate(expression)
        except PlaywrightError as exc:
            message = str(exc)
            if (
                "Execution context was destroyed" not in message
                and "Cannot read properties of null" not in message
            ):
                raise
            if attempt == 1:
                return None
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(1200)
    return None


async def scroll_search_page(
    page: Page,
    target_count: int,
    max_scrolls: int,
    protection: CrawlProtection,
) -> list[str]:
    collected: list[str] = []
    stagnant_rounds = 0

    for _ in range(max_scrolls):
        try:
            urls = await collect_note_urls(page)
        except PlaywrightError as exc:
            if "Execution context was destroyed" not in str(exc):
                raise
            await page.wait_for_load_state("domcontentloaded")
            await polite_delay(protection, multiplier=0.4)
            urls = await collect_note_urls(page)
        for url in urls:
            if url not in collected:
                collected.append(url)

        if len(collected) >= target_count:
            break

        await polite_delay(protection, multiplier=0.5)
        before_height = await safe_page_evaluate(
            page, "document.body ? document.body.scrollHeight : null"
        )
        if before_height is None:
            stagnant_rounds += 1
            if stagnant_rounds >= 3:
                break
            continue
        await safe_page_evaluate(
            page,
            "if (document.body) { window.scrollBy(0, Math.floor(window.innerHeight * 1.6)); }",
        )
        await polite_delay(protection, multiplier=0.5)
        second_scroll = await safe_page_evaluate(
            page,
            "if (document.body) { window.scrollBy(0, Math.floor(window.innerHeight * 0.4)); }",
        )
        if second_scroll is None:
            stagnant_rounds += 1
            if stagnant_rounds >= 3:
                break
            continue
        await polite_delay(protection, multiplier=0.4)
        after_height = await safe_page_evaluate(
            page, "document.body ? document.body.scrollHeight : null"
        )
        if after_height is None:
            stagnant_rounds += 1
            if stagnant_rounds >= 3:
                break
            continue

        if after_height == before_height and len(urls) == len(collected):
            stagnant_rounds += 1
            if stagnant_rounds >= 3:
                break
        else:
            stagnant_rounds = 0

    return collected[:target_count]


def is_search_response(url: str) -> bool:
    lowered = url.lower()
    return "xiaohongshu.com" in lowered and any(
        hint in lowered for hint in SEARCH_RESPONSE_HINTS
    )


async def extract_note_detail(
    context, keyword: str, record: NoteRecord, protection: CrawlProtection
) -> NoteRecord:
    page = await context.new_page()
    await _stealth.apply_stealth_async(page)
    payloads: list[dict[str, Any]] = []
    response_tasks: list[asyncio.Task] = []
    target_url = record.share_url or record.note_url

    async def on_response(response):
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        if "xiaohongshu.com" not in response.url:
            return
        try:
            payload = await response.json()
        except (PlaywrightError, Exception):
            return
        payloads.append(payload)

    def response_handler(response):
        response_tasks.append(asyncio.create_task(on_response(response)))

    page.on("response", response_handler)

    try:
        await polite_delay(protection, reason=f"访问详情页 {record.note_id}")
        await goto_with_retry(
            page,
            f"打开详情页 {record.note_id}",
            target_url,
            "domcontentloaded",
            60000,
            protection,
        )
        await polite_delay(protection, multiplier=0.7)
        if response_tasks:
            await asyncio.gather(*response_tasks, return_exceptions=True)

        payload_result = parse_note_from_payload(payloads)
        dom_text = await read_first_text(page, TEXT_SELECTORS)
        dom_time = await read_first_text(page, TIME_SELECTORS)
        dom_images = await collect_dom_image_urls(page)

        raw_text = payload_result["raw_text"] or dom_text
        image_urls = payload_result["image_urls"] or dom_images
        publish_timestamp = payload_result["publish_timestamp"]
        publish_time_text = dom_time or None

        return NoteRecord(
            keyword=keyword,
            note_id=record.note_id,
            note_url=record.note_url,
            share_url=record.share_url,
            xsec_token=record.xsec_token,
            can_open_in_web=record.can_open_in_web,
            title_text=record.title_text,
            raw_text=raw_text,
            text_source="detail_page" if raw_text else record.text_source,
            image_urls=image_urls,
            downloaded_image_paths=record.downloaded_image_paths,
            publish_timestamp=publish_timestamp,
            publish_time_text=publish_time_text,
            publish_time_resolved=resolve_publish_time_text(
                publish_time_text, publish_timestamp
            ),
        )
    finally:
        try:
            await page.close()
        except Exception:
            pass


async def collect_search_page_data(
    page: Page,
    target_count: int,
    max_scrolls: int,
    response_tasks: list[asyncio.Task],
    payloads: list[dict[str, Any]],
    protection: CrawlProtection,
) -> tuple[list[str], list[NoteRecord]]:
    note_urls = await scroll_search_page(
        page,
        target_count=target_count,
        max_scrolls=max_scrolls,
        protection=protection,
    )
    if response_tasks:
        await asyncio.gather(*response_tasks, return_exceptions=True)
    search_records = parse_search_results_from_payloads(payloads, keyword="")
    return note_urls, search_records


async def scrape_keyword(
    context,
    keyword: str,
    target_count: int,
    max_scrolls: int,
    allow_detail_fallback: bool,
    enrich_text_from_detail: bool,
    debug_dir: Path | None,
    protection: CrawlProtection,
    page: Page | None = None,
) -> list[NoteRecord]:
    owns_page = page is None
    if owns_page:
        page = await context.new_page()
        await _stealth.apply_stealth_async(page)
    payloads: list[dict[str, Any]] = []
    response_tasks: list[asyncio.Task] = []

    async def on_response(response):
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        if "xiaohongshu.com" in response.url:
            print(f"[DEBUG] API响应: {response.url[:120]}")
        if not is_search_response(response.url):
            return
        try:
            payload = await response.json()
        except (PlaywrightError, Exception):
            return
        payloads.append(payload)

    def response_handler(response):
        response_tasks.append(asyncio.create_task(on_response(response)))

    page.on("response", response_handler)

    search_url = SEARCH_URL.format(keyword=quote(keyword))
    try:
        await polite_delay(protection, reason=f"打开关键词 {keyword} 搜索页")
        await goto_with_retry(
            page,
            f"打开关键词 {keyword} 搜索页",
            search_url,
            "networkidle",
            60000,
            protection,
        )
        await polite_delay(protection, multiplier=1.2, reason="等待搜索页稳定加载")
        try:
            await page.screenshot(
                path=f"debug_{keyword.lstrip('#')}.png", full_page=False
            )
            print(f"[DEBUG] 截图已保存: debug_{keyword.lstrip('#')}.png")
        except Exception as exc:
            print(f"[WARN] 搜索页截图失败，继续执行: {exc}")
    except Exception as exc:
        print(f"[WARN] 关键词 {keyword} 搜索页打开失败，跳过该关键词: {exc}")
        remove_page_listener(page, "response", response_handler)
        if owns_page:
            await page.close()
        return []

    try:
        note_urls, _ = await collect_search_page_data(
            page, target_count, max_scrolls, response_tasks, payloads, protection
        )
    except Exception as exc:
        print(f"[WARN] 关键词 {keyword} 滚动采集异常，继续解析已捕获响应: {exc}")
        if response_tasks:
            await asyncio.gather(*response_tasks, return_exceptions=True)
        note_urls = []

    try:
        page_state_items = await extract_notes_from_page_state(page)
    except Exception as exc:
        page_state_items = []
        print(f"[WARN] 读取页面状态失败，继续使用接口响应: {exc}")
    if page_state_items:
        print(f"关键词 {keyword}: 从页面初始状态找到 {len(page_state_items)} 个候选对象")
        payloads.append({"page_state_items": page_state_items})

    search_records = parse_search_results_from_payloads(payloads, keyword)
    records_by_id = {
        record.note_id: record for record in search_records if record.note_id
    }
    records_by_url = {record.note_url: record for record in search_records}
    if debug_dir is not None:
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_path = (
                debug_dir
                / f"{keyword.lstrip('#').replace('/', '_')}_search_payloads.json"
            )
            debug_path.write_text(
                json.dumps(payloads, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            print(f"[WARN] 调试响应写入失败，继续执行: {exc}")
    print(
        f"关键词 {keyword}: 捕获搜索响应 {len(payloads)} 个，解析到搜索卡片 {len(search_records)} 条，页面链接 {len(note_urls)} 条"
    )
    remove_page_listener(page, "response", response_handler)
    if owns_page:
        await page.close()

    results: list[NoteRecord] = []
    detail_attempts = 0
    for url in note_urls:
        base_record = records_by_url.get(url)
        if base_record is None:
            note_id_match = re.search(r"/explore/([^/?]+)", url)
            note_id = note_id_match.group(1) if note_id_match else ""
            base_record = records_by_id.get(
                note_id,
                NoteRecord(
                    keyword=keyword,
                    note_id=note_id,
                    note_url=url,
                    share_url=None,
                    xsec_token=None,
                    can_open_in_web=False,
                    title_text=None,
                    raw_text="",
                    text_source="search_title",
                    image_urls=[],
                    downloaded_image_paths=[],
                    publish_timestamp=None,
                    publish_time_text=None,
                    publish_time_resolved=None,
                ),
            )

        should_enrich = enrich_text_from_detail and should_enrich_text_from_detail(
            base_record
        )

        if not allow_detail_fallback and not should_enrich:
            results.append(base_record)
            continue

        if (
            not should_enrich
            and base_record.raw_text
            and base_record.image_urls
            and base_record.publish_timestamp is not None
        ):
            results.append(base_record)
            continue

        try:
            detail_attempts += 1
            detail_record = await extract_note_detail(
                context, keyword, base_record, protection
            )
            results.append(merge_record(base_record, detail_record))
        except Exception as exc:
            results.append(base_record)
            print(f"跳过失败帖子: {url} | {exc}")

    if len(results) < target_count:
        for record in search_records:
            if record.note_url not in {item.note_url for item in results}:
                results.append(record)
            if len(results) >= target_count:
                break

    complete_count = sum(
        1
        for item in results
        if item.raw_text and item.image_urls and item.publish_timestamp is not None
    )
    print(
        f"关键词 {keyword}: 详情补采尝试 {detail_attempts} 条，最终输出 {len(results)} 条，其中完整记录 {complete_count} 条"
    )

    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="异步抓取小红书关键词帖子内容")
    parser.add_argument(
        "--max-notes", type=int, default=10, help="每个关键词最多抓取多少条帖子"
    )
    parser.add_argument(
        "--max-scrolls", type=int, default=20, help="搜索结果页最多滚动多少次"
    )
    parser.add_argument(
        "--headless", action="store_true", help="使用无头模式启动浏览器"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("xiaohongshu_results.json"),
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--allow-detail-fallback",
        action="store_true",
        help="允许在搜索页字段不足时访问详情页补采，默认关闭以避免 404 或仅 App 可见页面",
    )
    parser.add_argument(
        "--enrich-text-from-detail",
        action="store_true",
        help="对可网页访问的帖子补采详情页正文，获取比标题更完整的文字信息",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("xiaohongshu_debug"),
        help="保存搜索接口原始响应的目录，便于调试解析规则",
    )
    parser.add_argument(
        "--download-images",
        action="store_true",
        help="下载抓取到的图片到本地目录",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path("xiaohongshu_images"),
        help="图片下载目录",
    )
    parser.add_argument(
        "--max-images-per-note",
        type=int,
        default=20,
        help="每条帖子最多下载多少张图片",
    )
    parser.add_argument(
        "--storage-state",
        type=Path,
        default=DEFAULT_STORAGE_STATE,
        help="保存/读取登录态的文件；存在时后续运行不再要求人工登录",
    )
    parser.add_argument(
        "--force-login",
        action="store_true",
        help="忽略已有登录态，重新人工登录并覆盖保存",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY_SECONDS,
        help="页面访问、滚动、下载之间的最小随机等待秒数",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY_SECONDS,
        help="页面访问、滚动、下载之间的最大随机等待秒数",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="遇到网络/页面临时异常时的最大重试次数",
    )
    args = parser.parse_args()
    protection = CrawlProtection(
        min_delay_seconds=args.min_delay,
        max_delay_seconds=args.max_delay,
        max_retries=args.max_retries,
    )
    all_results: list[NoteRecord] = []

    async with async_playwright() as playwright:
        browser = None
        context = None
        login_page = None
        try:
            has_saved_login = args.storage_state.exists() and not args.force_login
            browser_headless = args.headless and has_saved_login
            if args.headless and not has_saved_login:
                print("[WARN] 未找到登录态，首次登录需要可视浏览器，本次自动使用非无头模式")

            browser = await playwright.chromium.launch(headless=browser_headless)
            context_options: dict[str, Any] = {
                "viewport": {"width": 1440, "height": 960},
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "locale": "zh-CN",
            }
            if has_saved_login:
                context_options["storage_state"] = str(args.storage_state)
                print(f"[PROTECT] 已加载登录态: {args.storage_state}")

            try:
                context = await browser.new_context(**context_options)
            except Exception as exc:
                if not has_saved_login:
                    raise
                print(f"[WARN] 登录态加载失败，将回到首次登录流程: {exc}")
                context_options.pop("storage_state", None)
                has_saved_login = False
                if browser_headless:
                    await browser.close()
                    browser = await playwright.chromium.launch(headless=False)
                    print("[WARN] 已切换到可视浏览器，请重新完成登录")
                context = await browser.new_context(**context_options)
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )

            login_page = await context.new_page()
            await _stealth.apply_stealth_async(login_page)
            await goto_with_retry(
                login_page,
                "打开小红书首页",
                "https://www.xiaohongshu.com",
                "domcontentloaded",
                60000,
                protection,
            )

            if not has_saved_login:
                await asyncio.to_thread(
                    input,
                    "请在浏览器中完成首次登录，完成后按回车保存登录态并开始抓取... ",
                )
                args.storage_state.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(args.storage_state))
                print(f"[PROTECT] 登录态已保存: {args.storage_state}")

            for keyword in SEARCH_KEYWORDS:
                print(f"开始抓取关键词: {keyword}")
                try:
                    keyword_results = await scrape_keyword(
                        context,
                        keyword,
                        args.max_notes,
                        args.max_scrolls,
                        args.allow_detail_fallback,
                        args.enrich_text_from_detail,
                        args.debug_dir,
                        protection,
                        page=login_page,
                    )
                    all_results.extend(keyword_results)
                    try:
                        await context.storage_state(path=str(args.storage_state))
                    except Exception as exc:
                        print(f"[WARN] 更新登录态失败，继续执行: {exc}")
                except Exception as exc:
                    print(f"[WARN] 关键词 {keyword} 抓取失败，继续下一个关键词: {exc}")
                    continue
        except Exception as exc:
            print(f"[WARN] 主流程遇到异常，保留已抓取结果并继续收尾: {exc}")
        finally:
            for resource_name, resource in (
                ("页面", login_page),
                ("上下文", context),
                ("浏览器", browser),
            ):
                if resource is None:
                    continue
                try:
                    await resource.close()
                except Exception as exc:
                    print(f"[WARN] 关闭{resource_name}失败，忽略: {exc}")

    if args.download_images:
        try:
            await download_record_images(
                all_results,
                args.image_dir,
                max_images_per_note=max(1, args.max_images_per_note),
                protection=protection,
            )
            print(f"图片下载完成，目录: {args.image_dir}")
        except Exception as exc:
            print(f"[WARN] 图片下载阶段失败，继续写入已抓取文本结果: {exc}")

    serialized = [asdict(item) for item in all_results]
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"抓取完成，共 {len(serialized)} 条，结果已保存到: {args.output}")
    except Exception as exc:
        fallback_output = Path("xiaohongshu_results_partial.json")
        try:
            fallback_output.write_text(
                json.dumps(serialized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(
                f"[WARN] 原输出写入失败: {exc}；已改存到: {fallback_output}"
            )
        except Exception as fallback_exc:
            print(f"[WARN] 结果写入失败，已抓取 {len(serialized)} 条: {fallback_exc}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[WARN] 收到手动中断，程序退出")
    except Exception as exc:
        print(f"[WARN] 未处理异常已捕获，程序退出但不抛出: {exc}")
