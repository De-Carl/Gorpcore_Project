"""
Node D: Text Analyzer 文本分析节点。

本节点目标：
1. 读取多平台文本数据（优先 master CSV，否则读取各平台 JSON）
2. 统一字段并清理文本
3. jieba 分词与词频统计
4. 痛点关键词提取与简单情感分析
5. 构建文本特征向量表
6. 输出清理文本、痛点表、情感标签、微本体、设计映射与分析报告

运行方式：
    python node_d_text_analyzer.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import jieba

from config import DATASET_ROOT, PROJECT_ROOT, ensure_output_dirs

# ============================================================
# 路径与输出配置
# ============================================================

AGENT_ROOT = PROJECT_ROOT / "Gorpcore_Agent"
TEXT_ANALYSIS_OUTPUT_DIR = AGENT_ROOT / "output" / "text_analysis"

MASTER_CSV = DATASET_ROOT / "v1" / "dataset_v1_master.csv"
XHS_JSON = DATASET_ROOT / "xhs" / "xiaohongshu_with_images.json"
TAOBAO_JSON = DATASET_ROOT / "taobao" / "taobao_reviews.json"
BILIBILI_JSON = DATASET_ROOT / "bilibili" / "bilibili_results.json"

CLEANED_TEXT_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "cleaned_text.csv"
TOKENIZED_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "tokenized_text.csv"
WORD_FREQUENCY_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "word_frequency.csv"
TEXT_FEATURE_VECTORS_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "text_feature_vectors.csv"
PAIN_POINT_TABLE_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "pain_point_table.csv"
SENTIMENT_LABELS_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "sentiment_labels.csv"
MICRO_ONTOLOGY_JSON = TEXT_ANALYSIS_OUTPUT_DIR / "micro_ontology.json"
PAINPOINT_DESIGN_MAPPING_CSV = TEXT_ANALYSIS_OUTPUT_DIR / "painpoint_design_mapping.csv"
TEXT_ANALYSIS_REPORT_MD = TEXT_ANALYSIS_OUTPUT_DIR / "text_analysis_report.md"

OUTPUT_FILE_NAMES = [
    CLEANED_TEXT_CSV.name,
    TOKENIZED_CSV.name,
    WORD_FREQUENCY_CSV.name,
    TEXT_FEATURE_VECTORS_CSV.name,
    PAIN_POINT_TABLE_CSV.name,
    SENTIMENT_LABELS_CSV.name,
    MICRO_ONTOLOGY_JSON.name,
    PAINPOINT_DESIGN_MAPPING_CSV.name,
    TEXT_ANALYSIS_REPORT_MD.name,
]

UNIFIED_FIELDS = ["Source_ID", "Platform", "Raw_Text", "Timestamp", "Data_Type"]

# ============================================================
# 痛点规则（关键词 -> 标准痛点标签）
# ============================================================

PAIN_POINT_RULES: List[Tuple[str, Sequence[str]]] = [
    ("不透气", ("不透气", "不透风", "闷热", "闷汗", "不通风", "憋闷")),
    ("太重", ("太重", "笨重", "沉重", "压身", "负重感")),
    ("不日透气常", ("不日透气常", "不日常", "不常穿", "难日常")),
    ("版型差", ("版型差", "版型不好", "版型怪", "显胖", "不合身", "剪裁差")),
    ("拉链问题", ("拉链问题", "拉链坏", "拉链卡", "拉锁", "拉链不顺", "拉链裂")),
    ("价格高", ("价格高", "太贵", "好贵", "性价比低", "不值", "买贵了", "贵死")),
    ("不耐磨", ("不耐磨", "起球", "易磨损", "不耐用", "质量差", "容易破")),
    ("不适合通勤", ("不适合通勤", "穿不出去", "没法通勤", "上班不能穿", "不实用")),
]

# ============================================================
# 情感词典
# ============================================================

POSITIVE_WORDS = {
    "好", "好看", "舒服", "舒适", "透气", "轻便", "轻", "满意", "喜欢", "推荐",
    "值得", "划算", "性价比", "耐穿", "耐磨", "百搭", "显瘦", "合身", "正品",
    "赞", "棒", "优秀", "完美", "惊艳", "回购", "爱了", "实用", "日常", "通勤",
}

# 负面短语：允许子串匹配（多字词）
NEGATIVE_PHRASES = {
    "难看", "不舒服", "失望", "后悔", "不推荐", "不值", "太贵", "好贵",
    "起球", "假货", "差评", "退款", "臃肿", "显胖", "不合身", "闷汗",
    "不透气", "笨重", "不实用", "买亏了", "质量差", "不值", "垃圾",
}

# 负面单字：仅在分词 token 中独立出现时计入，避免子串误报
NEGATIVE_SINGLE_CHARS = {
    "差", "闷", "贵", "破", "烂", "坑", "裂", "坏", "卡",
}

# “太重”类负面：必须整短语命中，禁止单独匹配“重”
WEIGHT_NEGATIVE_PHRASES = (
    "太重", "很重", "厚重", "压身", "笨重", "沉重", "负重感", "好重", "太重了",
    "很沉", "偏沉", "有点沉", "太沉",
)
# “沉”仅在分词为独立词时视为重量负面，避免命中“沉思”等词
WEIGHT_NEGATIVE_SINGLE_CHARS = ("沉",)

# 痛点 -> 设计映射（用于 painpoint_design_mapping.csv）
PAINPOINT_DESIGN_MAPPING: List[Dict[str, str]] = [
    {
        "Pain_Point": "不透气",
        "Design_Implication": "加强透气结构与通风设计",
        "Related_Elements": "透气膜 | 通风拉链 | 网眼内衬",
    },
    {
        "Pain_Point": "太重",
        "Design_Implication": "采用更轻量面料并优化裁片",
        "Related_Elements": "轻量尼龙 | 精简裁片 | 减少辅料克重",
    },
    {
        "Pain_Point": "不日透气常",
        "Design_Implication": "平衡户外性能与日常穿搭场景",
        "Related_Elements": "低调配色 | 可收纳帽 | 城市通勤口袋布局",
    },
    {
        "Pain_Point": "版型差",
        "Design_Implication": "优化版型与尺码梯度",
        "Related_Elements": "立体剪裁 | 多尺码梯度 | 肩腰比例调整",
    },
    {
        "Pain_Point": "拉链问题",
        "Design_Implication": "升级拉链五金与工艺质检",
        "Related_Elements": "YKK拉链 | 防水拉链 | 拉链挡片",
    },
    {
        "Pain_Point": "价格高",
        "Design_Implication": "明确价值点或提供更具竞争力的定价策略",
        "Related_Elements": "成本可视化 | 分层产品线 | 材料替代方案",
    },
    {
        "Pain_Point": "不耐磨",
        "Design_Implication": "提升耐磨面料与关键部位加固",
        "Related_Elements": "考杜拉 | 耐磨涂层 | 肘部膝部补强",
    },
    {
        "Pain_Point": "不适合通勤",
        "Design_Implication": "增加城市通勤友好的外观与收纳设计",
        "Related_Elements": "简约外观 | 电脑隔层 | 轻量通勤版型",
    },
]

PAINPOINT_DESIGN_LOOKUP = {row["Pain_Point"]: row for row in PAINPOINT_DESIGN_MAPPING}

# ============================================================
# 领域词表（用于特征向量）
# ============================================================

COLOR_TERMS = {
    "黑", "白色", "白", "灰", "军绿", "橄榄绿", "卡其", "藏青", "蓝", "红",
    "橙", "黄", "紫", "米白", "墨绿", "深灰", "浅灰", "军服绿", "撞色",
}

MATERIAL_TERMS = {
    "尼龙", "gore", "tex", "防水", "防风", "软壳", "硬壳", "抓绒", "羽绒",
    "棉", "涤纶", "聚酯", "膜", "涂层", "ripstop", "考杜拉", "面料", "材质",
}

FIT_TERMS = {
    "修身", "宽松", "oversize", "合身", "显瘦", "显胖", "版型", "剪裁",
    "直筒", "短款", "长款", "落肩", "收腰",
}

FUNCTION_TERMS = {
    "透气", "防水", "防风", "保暖", "防寒", "速干", "耐磨", "轻量", "收纳",
    "多口袋", "反光", "可拆卸", "拉链", "帽檐", "压胶", "密封",
}

SCENARIO_TERMS = {
    "通勤", "户外", "徒步", "登山", "城市", "日常", "露营", "骑行", "旅行",
    "上班", "街拍", "滑雪", "雨天", "冬季", "夏季",
}

GENERAL_KEYWORDS = {
    "机能风", "gorpcore", "gorp", "户外", "冲锋衣", "软壳", "硬壳", "穿搭",
    "始祖鸟", "萨洛蒙", "巴塔哥尼亚", "工装", "山系", "urban", "techwear",
}

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]+",
    flags=re.UNICODE,
)
GARBLED_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]")
REPEAT_PUNCT_PATTERN = re.compile(r"([，。！？、；：,.!?;:'\"])\1{1,}")
WHITESPACE_PATTERN = re.compile(r"\s+")


def ensure_text_analysis_output_dir() -> None:
    """确保文本分析输出目录存在。"""
    ensure_output_dirs()
    TEXT_ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_column_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _pick_field(row: Dict[str, Any], candidates: Sequence[str], default: str = "") -> str:
    normalized = {_normalize_column_name(k): v for k, v in row.items()}
    for candidate in candidates:
        value = normalized.get(_normalize_column_name(candidate))
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def load_from_master_csv(csv_path: Path) -> List[Dict[str, str]]:
    """从 dataset_v1_master.csv 读取已统一格式的数据。"""
    records: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for index, row in enumerate(reader, start=1):
            source_id = _pick_field(
                row,
                ("Source_ID", "source_id", "id", "record_id"),
                default=f"GRP-MASTER-{index:06d}",
            )
            platform = _pick_field(row, ("Platform", "platform"), default="unknown")
            raw_text = _pick_field(
                row,
                ("Raw_Text", "raw_text", "text", "content", "body"),
            )
            timestamp = _pick_field(
                row,
                ("Timestamp", "timestamp", "time", "publish_time", "creation_time"),
            )
            data_type = _pick_field(
                row,
                ("Data_Type", "data_type", "type"),
                default="text",
            )
            if not raw_text:
                continue
            records.append(
                {
                    "Source_ID": source_id,
                    "Platform": platform,
                    "Raw_Text": raw_text,
                    "Timestamp": timestamp,
                    "Data_Type": data_type,
                }
            )
    return records


def load_from_xhs_json(json_path: Path) -> List[Dict[str, str]]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{json_path} 顶层结构应为 list。")

    records: List[Dict[str, str]] = []
    for note in data:
        note_id = str(note.get("note_id", "")).strip() or "unknown_note"
        title = str(note.get("title_text", "")).strip()
        body = str(note.get("raw_text", "")).strip()
        parts: List[str] = []
        if title:
            parts.append(title)
        if body and body != title:
            parts.append(body)
        raw_text = "\n".join(parts).strip()
        if not raw_text:
            continue
        timestamp = str(
            note.get("publish_time_resolved")
            or note.get("publish_time_text")
            or note.get("publish_timestamp")
            or ""
        ).strip()
        records.append(
            {
                "Source_ID": f"GRP-XHS-{note_id}",
                "Platform": "xiaohongshu",
                "Raw_Text": raw_text,
                "Timestamp": timestamp,
                "Data_Type": "note",
            }
        )
    return records


def load_from_taobao_json(json_path: Path) -> List[Dict[str, str]]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    reviews = data.get("reviews", []) if isinstance(data, dict) else []
    records: List[Dict[str, str]] = []
    for index, review in enumerate(reviews, start=1):
        content = str(review.get("content", "")).strip()
        if not content:
            continue
        product_id = str(review.get("product_id", "")).strip() or "unknown_product"
        records.append(
            {
                "Source_ID": f"GRP-TB-{product_id}-{index:04d}",
                "Platform": "taobao",
                "Raw_Text": content,
                "Timestamp": str(review.get("creation_time", "")).strip(),
                "Data_Type": "review",
            }
        )
    return records


def load_from_bilibili_json(json_path: Path) -> List[Dict[str, str]]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{json_path} 顶层结构应为 dict。")

    records: List[Dict[str, str]] = []

    for index, item in enumerate(data.get("all_danmaku", []), start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        bvid = str(item.get("bvid", "")).strip() or "unknown_bvid"
        records.append(
            {
                "Source_ID": f"GRP-BILI-DM-{bvid}-{index:06d}",
                "Platform": "bilibili",
                "Raw_Text": text,
                "Timestamp": "",
                "Data_Type": "danmaku",
            }
        )

    for index, item in enumerate(data.get("all_comments", []), start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        bvid = str(item.get("bvid", "")).strip() or "unknown_bvid"
        records.append(
            {
                "Source_ID": f"GRP-BILI-CM-{bvid}-{index:06d}",
                "Platform": "bilibili",
                "Raw_Text": text,
                "Timestamp": "",
                "Data_Type": "comment",
            }
        )
    return records


def load_unified_records() -> Tuple[List[Dict[str, str]], str]:
    """
    加载并统一多平台文本记录。

    返回:
        (records, source_description)
    """
    if MASTER_CSV.exists():
        records = load_from_master_csv(MASTER_CSV)
        return records, str(MASTER_CSV)

    records: List[Dict[str, str]] = []
    sources: List[str] = []

    if XHS_JSON.exists():
        records.extend(load_from_xhs_json(XHS_JSON))
        sources.append(str(XHS_JSON))
    if TAOBAO_JSON.exists():
        records.extend(load_from_taobao_json(TAOBAO_JSON))
        sources.append(str(TAOBAO_JSON))
    if BILIBILI_JSON.exists():
        records.extend(load_from_bilibili_json(BILIBILI_JSON))
        sources.append(str(BILIBILI_JSON))

    if not records:
        raise FileNotFoundError(
            "未找到可用文本数据源。请提供 Dataset/v1/dataset_v1_master.csv，"
            "或确保 xhs / taobao / bilibili JSON 文件存在。"
        )

    return records, " | ".join(sources)


def clean_text(text: str) -> str:
    """清理文本：HTML、表情、乱码、空格与重复标点。"""
    if not text:
        return ""

    cleaned = HTML_TAG_PATTERN.sub(" ", text)
    cleaned = EMOJI_PATTERN.sub(" ", cleaned)
    cleaned = GARBLED_PATTERN.sub(" ", cleaned)
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    def _collapse_punct(match: re.Match[str]) -> str:
        return match.group(1)

    cleaned = REPEAT_PUNCT_PATTERN.sub(_collapse_punct, cleaned)
    return cleaned.strip()


def tokenize_text(text: str) -> List[str]:
    """使用 jieba 分词，过滤空白与单字符噪声（保留常见领域单字）。"""
    if not text:
        return []
    tokens: List[str] = []
    for token in jieba.lcut(text):
        word = token.strip()
        if not word:
            continue
        if len(word) == 1 and not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", word):
            continue
        tokens.append(word)
    return tokens


def _match_keywords_in_text(text: str, keywords: Sequence[str]) -> List[str]:
    """返回文本中命中的关键词列表。"""
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in text or keyword in lowered]


def _pain_point_confidence(matched_keywords: Sequence[str]) -> float:
    """根据命中关键词数量与长度估算置信度。"""
    if not matched_keywords:
        return 0.0
    longest = max(len(keyword) for keyword in matched_keywords)
    score = 0.72 + min(longest, 6) * 0.03 + (len(matched_keywords) - 1) * 0.05
    return round(min(score, 0.98), 2)


def extract_pain_point_details(text: str) -> List[Dict[str, Any]]:
    """
    根据关键词规则提取痛点，并附带证据词与置信度。

    返回列表元素示例：
        {"Pain_Point": "太重", "Evidence_Keyword": "笨重", "Confidence": 0.87}
    """
    details: List[Dict[str, Any]] = []
    for label, keywords in PAIN_POINT_RULES:
        matched = _match_keywords_in_text(text, keywords)
        if not matched:
            continue
        evidence = max(matched, key=len)
        details.append(
            {
                "Pain_Point": label,
                "Evidence_Keyword": evidence,
                "Confidence": _pain_point_confidence(matched),
            }
        )
    return details


def extract_pain_point_labels(text: str) -> List[str]:
    """仅返回痛点标签列表。"""
    return [item["Pain_Point"] for item in extract_pain_point_details(text)]


def find_positive_hits(text: str, tokens: Sequence[str]) -> List[str]:
    token_set = set(tokens)
    hits: List[str] = []
    for word in POSITIVE_WORDS:
        if len(word) == 1:
            if word in token_set:
                hits.append(word)
        elif word in text:
            hits.append(word)
    return sorted(set(hits))


def find_negative_hits(text: str, tokens: Sequence[str]) -> List[str]:
    """
    查找负面表达。

    规则：
    - 多字负面词：子串匹配
    - 单字负面词：仅当作为独立 token 出现时匹配
    - “重”相关：仅匹配 WEIGHT_NEGATIVE_PHRASES，禁止单独“重”
    """
    token_set = set(tokens)
    hits: List[str] = []

    for phrase in NEGATIVE_PHRASES:
        if phrase in text:
            hits.append(phrase)

    for phrase in WEIGHT_NEGATIVE_PHRASES:
        if phrase in text:
            hits.append(phrase)

    for char in WEIGHT_NEGATIVE_SINGLE_CHARS:
        if char in token_set:
            hits.append(char)

    for char in NEGATIVE_SINGLE_CHARS:
        if char in token_set:
            hits.append(char)

    return sorted(set(hits))


def analyze_sentiment(text: str, tokens: Sequence[str]) -> Tuple[str, float, str]:
    """
    基于正负面词典的简单情感分析。

    返回:
        (sentiment_label, sentiment_score, reason)
    """
    pos_hits = find_positive_hits(text, tokens)
    neg_hits = find_negative_hits(text, tokens)

    pos_count = len(pos_hits)
    neg_count = len(neg_hits)
    total = pos_count + neg_count

    if total == 0:
        return "neutral", 0.0, "未命中正负面词典"

    score = (pos_count - neg_count) / total
    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"

    reason_parts: List[str] = []
    if pos_hits:
        reason_parts.append(f"正面词：{', '.join(pos_hits[:5])}")
    if neg_hits:
        reason_parts.append(f"负面词：{', '.join(neg_hits[:5])}")
    reason = "；".join(reason_parts) if reason_parts else "正负面词数量接近"
    return label, round(score, 4), reason


def match_terms(text: str, tokens: Sequence[str], term_dict: Iterable[str]) -> List[str]:
    token_set = set(tokens)
    hits = [term for term in term_dict if term in text or term in token_set]
    return sorted(set(hits), key=len, reverse=True)


def extract_keywords(text: str, tokens: Sequence[str]) -> List[str]:
    keyword_hits = match_terms(text, tokens, GENERAL_KEYWORDS)
    domain_hits = (
        match_terms(text, tokens, COLOR_TERMS)
        + match_terms(text, tokens, MATERIAL_TERMS)
        + match_terms(text, tokens, FUNCTION_TERMS)
        + match_terms(text, tokens, SCENARIO_TERMS)
    )
    merged = keyword_hits + [term for term in domain_hits if term not in keyword_hits]
    return merged[:12]


def build_micro_ontology() -> Dict[str, List[str]]:
    """构建微本体 JSON 结构。"""
    return {
        "颜色": sorted(COLOR_TERMS),
        "材质": sorted(MATERIAL_TERMS),
        "剪裁": sorted(FIT_TERMS),
        "功能组件": sorted(FUNCTION_TERMS),
        "使用场景": sorted(SCENARIO_TERMS),
        "用户痛点": [label for label, _ in PAIN_POINT_RULES],
    }


def build_design_implications(
    pain_points: Sequence[str],
    sentiment: str,
    function_terms: Sequence[str],
    scenario_terms: Sequence[str],
) -> str:
    """根据痛点与情感生成简要设计启示。"""
    implications: List[str] = []

    for pain in pain_points:
        mapping = PAINPOINT_DESIGN_LOOKUP.get(pain)
        if mapping:
            implications.append(mapping["Design_Implication"])

    if sentiment == "negative" and not implications:
        implications.append("关注用户负面反馈并迭代体验细节")
    if sentiment == "positive" and function_terms:
        implications.append(f"延续受欢迎功能：{'、'.join(function_terms[:3])}")
    if scenario_terms and "通勤" in scenario_terms:
        implications.append("继续强化通勤场景的舒适与外观平衡")

    if not implications:
        return "暂无明显设计启示，建议结合更多样本"
    return "；".join(dict.fromkeys(implications))


def join_terms(terms: Sequence[str]) -> str:
    return " | ".join(terms) if terms else ""


def process_records(records: List[Dict[str, str]]) -> Tuple[Dict[str, Any], Counter]:
    """执行清理、分词、痛点与情感分析，构建全部中间结果。"""
    cleaned_rows: List[Dict[str, Any]] = []
    tokenized_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []
    pain_point_rows: List[Dict[str, Any]] = []
    sentiment_rows: List[Dict[str, Any]] = []
    word_counter: Counter = Counter()
    platform_processed: Counter = Counter()
    pain_point_counter: Counter = Counter()
    sentiment_counter: Counter = Counter()

    for record in records:
        source_id = record["Source_ID"]
        platform = record["Platform"]
        raw_text = record["Raw_Text"]
        timestamp = record.get("Timestamp", "")
        data_type = record.get("Data_Type", "")
        cleaned = clean_text(raw_text)
        if not cleaned:
            continue

        platform_processed[platform] += 1

        tokens = tokenize_text(cleaned)
        tokenized_text = " ".join(tokens)
        word_counter.update(tokens)

        pain_details = extract_pain_point_details(cleaned)
        pain_points = [item["Pain_Point"] for item in pain_details]
        sentiment, sentiment_score, reason = analyze_sentiment(cleaned, tokens)
        sentiment_counter[sentiment] += 1

        for detail in pain_details:
            pain_point_counter[detail["Pain_Point"]] += 1
            pain_point_rows.append(
                {
                    "Source_ID": source_id,
                    "Platform": platform,
                    "Cleaned_Text": cleaned,
                    "Pain_Point": detail["Pain_Point"],
                    "Evidence_Keyword": detail["Evidence_Keyword"],
                    "Confidence": detail["Confidence"],
                }
            )

        color_terms = match_terms(cleaned, tokens, COLOR_TERMS)
        material_terms = match_terms(cleaned, tokens, MATERIAL_TERMS)
        fit_terms = match_terms(cleaned, tokens, FIT_TERMS)
        function_terms = match_terms(cleaned, tokens, FUNCTION_TERMS)
        scenario_terms = match_terms(cleaned, tokens, SCENARIO_TERMS)
        keywords = extract_keywords(cleaned, tokens)

        design_implications = build_design_implications(
            pain_points, sentiment, function_terms, scenario_terms
        )

        cleaned_rows.append(
            {
                "Source_ID": source_id,
                "Platform": platform,
                "Raw_Text": raw_text,
                "Cleaned_Text": cleaned,
                "Timestamp": timestamp,
                "Data_Type": data_type,
            }
        )

        tokenized_rows.append(
            {
                "Source_ID": source_id,
                "Platform": platform,
                "Cleaned_Text": cleaned,
                "Tokens": tokenized_text,
            }
        )

        sentiment_rows.append(
            {
                "Source_ID": source_id,
                "Sentiment": sentiment,
                "Sentiment_Score": sentiment_score,
                "Reason": reason,
            }
        )

        feature_rows.append(
            {
                "Source_ID": source_id,
                "Platform": platform,
                "Cleaned_Text": cleaned,
                "Keywords": join_terms(keywords),
                "Pain_Points": join_terms(pain_points),
                "Sentiment": sentiment,
                "Sentiment_Score": sentiment_score,
                "Reason": reason,
                "Color_Terms": join_terms(color_terms),
                "Material_Terms": join_terms(material_terms),
                "Fit_Terms": join_terms(fit_terms),
                "Function_Terms": join_terms(function_terms),
                "Scenario_Terms": join_terms(scenario_terms),
                "Design_Implications": design_implications,
            }
        )

    return {
        "cleaned_rows": cleaned_rows,
        "tokenized_rows": tokenized_rows,
        "feature_rows": feature_rows,
        "pain_point_rows": pain_point_rows,
        "sentiment_rows": sentiment_rows,
        "platform_processed": platform_processed,
        "pain_point_counter": pain_point_counter,
        "sentiment_counter": sentiment_counter,
    }, word_counter


def count_platforms(records: Sequence[Dict[str, str]]) -> Counter:
    return Counter(record["Platform"] for record in records)


def write_text_analysis_report(
    path: Path,
    *,
    source_desc: str,
    input_records: int,
    processed_records: int,
    platform_input: Counter,
    platform_processed: Counter,
    top_words: Sequence[Tuple[str, int]],
    pain_point_counter: Counter,
    sentiment_counter: Counter,
    output_files: Sequence[str],
) -> None:
    """生成 text_analysis_report.md。"""
    lines: List[str] = [
        "# Node D 文本分析报告",
        "",
        "## 数据概览",
        "",
        f"- **输入数据来源**：{source_desc}",
        f"- **输入总条数**：{input_records}",
        f"- **有效分析条数**：{processed_records}",
        "",
        "## 各平台文本数量",
        "",
        "### 输入阶段",
        "",
    ]

    for platform, count in platform_input.most_common():
        lines.append(f"- {platform}: {count}")
    if not platform_input:
        lines.append("- （无）")

    lines.extend(["", "### 有效分析阶段", ""])
    for platform, count in platform_processed.most_common():
        lines.append(f"- {platform}: {count}")
    if not platform_processed:
        lines.append("- （无）")

    lines.extend(["", "## Top 20 高频词", ""])
    for rank, (word, count) in enumerate(top_words[:20], start=1):
        lines.append(f"{rank}. {word} ({count})")
    if not top_words:
        lines.append("- （无）")

    lines.extend(["", "## 各痛点数量", ""])
    if pain_point_counter:
        for pain, count in pain_point_counter.most_common():
            lines.append(f"- {pain}: {count}")
    else:
        lines.append("- （未命中痛点）")

    lines.extend(["", "## 情感分布", ""])
    total_sentiment = sum(sentiment_counter.values()) or 1
    for label in ("positive", "neutral", "negative"):
        count = sentiment_counter.get(label, 0)
        ratio = count / total_sentiment * 100
        lines.append(f"- {label}: {count} ({ratio:.1f}%)")

    lines.extend(["", "## 输出文件列表", ""])
    for filename in output_files:
        lines.append(f"- `{filename}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def run_text_analysis() -> Dict[str, Any]:
    """执行完整文本分析流程并写入输出文件。"""
    ensure_text_analysis_output_dir()

    records, source_desc = load_unified_records()
    platform_input = count_platforms(records)
    result, word_counter = process_records(records)
    top_words = word_counter.most_common(20)

    save_csv(
        CLEANED_TEXT_CSV,
        ["Source_ID", "Platform", "Raw_Text", "Cleaned_Text", "Timestamp", "Data_Type"],
        result["cleaned_rows"],
    )
    save_csv(
        TOKENIZED_CSV,
        ["Source_ID", "Platform", "Cleaned_Text", "Tokens"],
        result["tokenized_rows"],
    )
    save_csv(
        WORD_FREQUENCY_CSV,
        ["Word", "Frequency"],
        [{"Word": word, "Frequency": count} for word, count in word_counter.most_common()],
    )
    save_csv(
        TEXT_FEATURE_VECTORS_CSV,
        [
            "Source_ID",
            "Platform",
            "Cleaned_Text",
            "Keywords",
            "Pain_Points",
            "Sentiment",
            "Sentiment_Score",
            "Reason",
            "Color_Terms",
            "Material_Terms",
            "Fit_Terms",
            "Function_Terms",
            "Scenario_Terms",
            "Design_Implications",
        ],
        result["feature_rows"],
    )
    save_csv(
        PAIN_POINT_TABLE_CSV,
        [
            "Source_ID",
            "Platform",
            "Cleaned_Text",
            "Pain_Point",
            "Evidence_Keyword",
            "Confidence",
        ],
        result["pain_point_rows"],
    )
    save_csv(
        SENTIMENT_LABELS_CSV,
        ["Source_ID", "Sentiment", "Sentiment_Score", "Reason"],
        result["sentiment_rows"],
    )
    save_csv(
        PAINPOINT_DESIGN_MAPPING_CSV,
        ["Pain_Point", "Design_Implication", "Related_Elements"],
        PAINPOINT_DESIGN_MAPPING,
    )

    with MICRO_ONTOLOGY_JSON.open("w", encoding="utf-8") as f:
        json.dump(build_micro_ontology(), f, ensure_ascii=False, indent=2)

    write_text_analysis_report(
        TEXT_ANALYSIS_REPORT_MD,
        source_desc=source_desc,
        input_records=len(records),
        processed_records=len(result["feature_rows"]),
        platform_input=platform_input,
        platform_processed=result["platform_processed"],
        top_words=top_words,
        pain_point_counter=result["pain_point_counter"],
        sentiment_counter=result["sentiment_counter"],
        output_files=OUTPUT_FILE_NAMES,
    )

    return {
        "source": source_desc,
        "input_records": len(records),
        "processed_records": len(result["feature_rows"]),
        "pain_point_hits": len(result["pain_point_rows"]),
        "unique_tokens": len(word_counter),
        "output_dir": str(TEXT_ANALYSIS_OUTPUT_DIR),
    }


def main() -> None:
    """命令行入口。"""
    print("Node D: 文本分析开始...")
    summary = run_text_analysis()
    print(f"数据源: {summary['source']}")
    print(f"输入记录数: {summary['input_records']}")
    print(f"有效分析记录数: {summary['processed_records']}")
    print(f"痛点命中行数: {summary['pain_point_hits']}")
    print(f"唯一词数: {summary['unique_tokens']}")
    print(f"输出目录: {summary['output_dir']}")
    print("生成文件:")
    for filename in OUTPUT_FILE_NAMES:
        print(f"  - {filename}")
    print("Node D: 文本分析完成。")


if __name__ == "__main__":
    main()
