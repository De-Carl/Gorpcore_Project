"""
Member E: evidence fusion and early visual displays.

This script reads existing Node A/B/C/D outputs, extracts local image color
features, summarizes component evidence, builds a fused feature database, and
exports early insight charts.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_DIR / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
import seaborn as sns
from PIL import Image, UnidentifiedImageError
from sklearn.cluster import MiniBatchKMeans
from wordcloud import WordCloud


IMAGE_INDEX_CSV = PROJECT_ROOT / "Gorpcore_Agent" / "output" / "image_index.csv"
QUALITY_FILTERED_CSV = PROJECT_ROOT / "Gorpcore_Agent" / "output" / "quality_filtered_images.csv"
JSON_LABEL_DIR = PROJECT_ROOT / "Gorpcore_Agent" / "output" / "json_labels"
CROSS_CHECKED_CSV = PROJECT_ROOT / "Gorpcore_Agent" / "output" / "cross_checked_records.csv"
TEXT_ANALYSIS_DIR = (
    PROJECT_ROOT / "Gorpcore_Agent" / "text_analysis" / "output" / "text_analysis"
)
TEXT_FEATURE_CSV = TEXT_ANALYSIS_DIR / "text_feature_vectors.csv"
PAIN_POINT_CSV = TEXT_ANALYSIS_DIR / "pain_point_table.csv"
WORD_FREQUENCY_CSV = TEXT_ANALYSIS_DIR / "word_frequency.csv"
DATASET_XHS_DIR = PROJECT_ROOT / "Dataset" / "xhs"

COLOR_FEATURES_CSV = OUTPUT_DIR / "color_features.csv"
COMPONENT_SUMMARY_CSV = OUTPUT_DIR / "component_summary.csv"
FEATURE_DATABASE_CSV = OUTPUT_DIR / "feature_database.csv"
SUMMARY_JSON = OUTPUT_DIR / "member_e_summary.json"

PAIN_POINT_ENGLISH_LABELS = {
    "价格高": "High price",
    "不透气": "Not breathable",
    "不适合通勤": "Not commute-friendly",
    "太重": "Too heavy",
    "不耐磨": "Not durable",
    "版型差": "Poor fit",
    "拉链问题": "Zipper issues",
    "不日透气常": "Not everyday wearable",
}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)


def project_relative(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return path_obj.resolve().relative_to(PROJECT_ROOT).as_posix()
    except (OSError, ValueError):
        return str(path).replace(str(PROJECT_ROOT) + "/", "")


def normalize_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def source_id_from_image_id(image_id: str) -> str:
    parts = str(image_id).split("-")
    if len(parts) <= 1:
        return image_id
    return "-".join(parts[:-1])


def resolve_local_image_path(row: pd.Series) -> Path:
    relative_path = str(row.get("relative_image_path", "")).strip()
    if relative_path:
        normalized = Path(*re.split(r"[\\/]+", relative_path))
        return DATASET_XHS_DIR / normalized

    raw_path = str(row.get("image_path", "")).strip()
    if raw_path:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate
        marker = "xiaohongshu_images"
        if marker in raw_path:
            suffix = raw_path.split(marker, 1)[1].lstrip("\\/")
            return DATASET_XHS_DIR / marker / Path(*re.split(r"[\\/]+", suffix))

    return Path()


def rgb_to_hex(rgb: Iterable[float]) -> str:
    r, g, b = [max(0, min(255, int(round(v)))) for v in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def color_name_and_family(rgb: Iterable[float]) -> Tuple[str, str]:
    r, g, b = [float(v) / 255.0 for v in rgb]
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    chroma = max_c - min_c
    value = max_c
    saturation = 0.0 if value == 0 else chroma / value

    if value < 0.18:
        return "black", "black"
    if saturation < 0.12:
        if value > 0.82:
            return "white", "white"
        return "gray", "gray"

    import colorsys

    hue = colorsys.rgb_to_hsv(r, g, b)[0] * 360
    if hue < 15 or hue >= 345:
        return "red", "red_or_orange"
    if hue < 35:
        return "orange", "red_or_orange"
    if hue < 55:
        if value < 0.48:
            return "brown", "brown"
        if saturation < 0.45:
            return "khaki", "khaki_or_beige"
        return "yellow", "yellow"
    if hue < 85:
        if saturation < 0.45:
            return "olive", "olive_or_green"
        return "yellow green", "olive_or_green"
    if hue < 165:
        return "green", "olive_or_green"
    if hue < 255:
        return "blue", "blue"
    if hue < 310:
        return "purple", "purple"
    return "pink", "red_or_orange"


def extract_color_features(image_path: Path) -> Dict[str, Any]:
    if not image_path or not image_path.exists():
        return {
            "Primary_HEX": "",
            "Secondary_HEX": "",
            "Dominant_Color_Name": "unknown",
            "Color_Family": "unknown",
            "Primary_Color_Ratio": 0.0,
            "Secondary_Color_Ratio": 0.0,
            "Color_Extraction_Status": "missing_file",
        }

    try:
        with Image.open(image_path) as img:
            image = img.convert("RGB")
            image.thumbnail((256, 256))
            pixels = np.asarray(image).reshape(-1, 3)
    except (OSError, UnidentifiedImageError):
        return {
            "Primary_HEX": "",
            "Secondary_HEX": "",
            "Dominant_Color_Name": "unknown",
            "Color_Family": "unknown",
            "Primary_Color_Ratio": 0.0,
            "Secondary_Color_Ratio": 0.0,
            "Color_Extraction_Status": "image_read_error",
        }

    if len(pixels) == 0:
        return {
            "Primary_HEX": "",
            "Secondary_HEX": "",
            "Dominant_Color_Name": "unknown",
            "Color_Family": "unknown",
            "Primary_Color_Ratio": 0.0,
            "Secondary_Color_Ratio": 0.0,
            "Color_Extraction_Status": "empty_image",
        }

    sample_size = min(len(pixels), 5000)
    rng = np.random.default_rng(42)
    sample_indices = rng.choice(len(pixels), size=sample_size, replace=False)
    sampled_pixels = pixels[sample_indices]

    cluster_count = min(5, len(np.unique(sampled_pixels, axis=0)))
    if cluster_count <= 1:
        primary_rgb = sampled_pixels[0]
        secondary_rgb = sampled_pixels[0]
        primary_ratio = 1.0
        secondary_ratio = 0.0
    else:
        model = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=42,
            n_init=5,
            batch_size=1024,
        )
        labels = model.fit_predict(sampled_pixels)
        counts = np.bincount(labels, minlength=cluster_count)
        order = np.argsort(counts)[::-1]
        primary_idx = int(order[0])
        secondary_idx = int(order[1]) if len(order) > 1 else primary_idx
        primary_rgb = model.cluster_centers_[primary_idx]
        secondary_rgb = model.cluster_centers_[secondary_idx]
        primary_ratio = float(counts[primary_idx] / counts.sum())
        secondary_ratio = float(counts[secondary_idx] / counts.sum())

    color_name, color_family = color_name_and_family(primary_rgb)
    return {
        "Primary_HEX": rgb_to_hex(primary_rgb),
        "Secondary_HEX": rgb_to_hex(secondary_rgb),
        "Dominant_Color_Name": color_name,
        "Color_Family": color_family,
        "Primary_Color_Ratio": round(primary_ratio, 4),
        "Secondary_Color_Ratio": round(secondary_ratio, 4),
        "Color_Extraction_Status": "ok",
    }


def load_json_labels() -> Dict[str, Dict[str, Any]]:
    labels: Dict[str, Dict[str, Any]] = {}
    if not JSON_LABEL_DIR.exists():
        return labels

    for path in sorted(JSON_LABEL_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        image_id = str(data.get("Image_ID") or path.stem)
        labels[image_id] = data
    return labels


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def detect_text_components(text: str) -> Dict[str, bool]:
    lowered = text.lower()
    return {
        "Drawcord": any(term in lowered for term in ["抽绳", "束带", "drawstring", "cord"]),
        "Buckle": any(term in lowered for term in ["卡扣", "扣具", "buckle"]),
        "Reflective": any(term in lowered for term in ["反光", "reflective"]),
        "Hood": any(term in lowered for term in ["帽子", "连帽", "hood", "hooded"]),
    }


def infer_scenario_from_terms(value: Any) -> str:
    text = normalize_text(value).lower()
    if not text:
        return "Unclear"
    if any(term in text for term in ["通勤", "commute", "城市", "urban"]):
        return "Urban_Commute"
    if any(term in text for term in ["户外", "outdoor", "徒步", "露营", "登山"]):
        return "Outdoor"
    if any(term in text for term in ["运动", "sports", "跑步"]):
        return "Sports"
    if any(term in text for term in ["街", "street", "穿搭", "fashion"]):
        return "Fashion_Street"
    if any(term in text for term in ["办公室", "office", "上班"]):
        return "Office"
    return "Unclear"


def infer_fit_from_terms(value: Any) -> str:
    text = normalize_text(value).lower()
    if not text:
        return "Unclear"
    if any(term in text for term in ["宽松", "loose"]):
        return "Loose"
    if any(term in text for term in ["oversize", "oversized", "落肩"]):
        return "Oversized"
    if any(term in text for term in ["修身", "tight"]):
        return "Tight"
    if any(term in text for term in ["合身", "regular"]):
        return "Regular"
    if any(term in text for term in ["短款", "cropped"]):
        return "Cropped"
    return "Unclear"


def build_component_row(
    base_row: pd.Series,
    label: Optional[Dict[str, Any]],
    text_feature: Optional[pd.Series],
) -> Dict[str, Any]:
    image_id = normalize_text(base_row.get("Image_ID"))
    note_id = normalize_text(base_row.get("note_id"))
    text_blob = " ".join(
        [
            normalize_text(base_row.get("title_text")),
            normalize_text(base_row.get("raw_text")),
            normalize_text(text_feature.get("Cleaned_Text") if text_feature is not None else ""),
            normalize_text(text_feature.get("Keywords") if text_feature is not None else ""),
            normalize_text(text_feature.get("Function_Terms") if text_feature is not None else ""),
        ]
    )
    text_components = detect_text_components(text_blob)

    if label:
        return {
            "Image_ID": image_id,
            "note_id": note_id,
            "Pockets": label.get("Pockets", 0),
            "Zipper_Type": label.get("Zipper_Type", "Unclear"),
            "Drawcord": text_components["Drawcord"],
            "Buckle": text_components["Buckle"],
            "Reflective": bool(label.get("Reflective", False)) or text_components["Reflective"],
            "Hood": text_components["Hood"],
            "Fit": label.get("Fit", "Unclear"),
            "Scenario": label.get("Scenario", "Unclear"),
            "Visual_Weight": label.get("Visual_Weight", "unclear"),
            "Component_Source": "node_b",
            "Component_Confidence": float(label.get("Confidence", 0.0) or 0.0),
            "Component_Notes": "Visual label available; Drawcord/Buckle/Hood may use text evidence.",
        }

    has_text_evidence = any(text_components.values())
    fit = infer_fit_from_terms(text_feature.get("Fit_Terms") if text_feature is not None else "")
    scenario = infer_scenario_from_terms(
        text_feature.get("Scenario_Terms") if text_feature is not None else ""
    )
    has_text_evidence = has_text_evidence or fit != "Unclear" or scenario != "Unclear"

    return {
        "Image_ID": image_id,
        "note_id": note_id,
        "Pockets": "unknown",
        "Zipper_Type": "Unclear",
        "Drawcord": text_components["Drawcord"],
        "Buckle": text_components["Buckle"],
        "Reflective": text_components["Reflective"],
        "Hood": text_components["Hood"],
        "Fit": fit,
        "Scenario": scenario,
        "Visual_Weight": "unclear",
        "Component_Source": "text_heuristic" if has_text_evidence else "unknown",
        "Component_Confidence": 0.4 if has_text_evidence else 0.0,
        "Component_Notes": (
            "Component fields inferred from text evidence only."
            if has_text_evidence
            else "No component evidence available in current data."
        ),
    }


def split_terms(value: Any) -> List[str]:
    text = normalize_text(value)
    if not text:
        return []
    parts = re.split(r"[|,，;；\s]+", text)
    return [part.strip() for part in parts if part.strip()]


def first_nonempty(*values: Any) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def save_bar_chart(
    counts: pd.Series,
    title: str,
    output_path: Path,
    xlabel: str = "Count",
    horizontal: bool = False,
    palette: Optional[List[str]] = None,
) -> None:
    plt.figure(figsize=(9, 5.2), dpi=180)
    sns.set_theme(style="whitegrid", font=DEFAULT_FONT_FAMILY)
    counts = counts[counts.index.astype(str) != ""]
    if counts.empty:
        counts = pd.Series({"No data": 1})

    if horizontal:
        counts = counts.sort_values()
        colors = palette if palette else sns.color_palette("crest", len(counts))
        ax = plt.barh(counts.index.astype(str), counts.values, color=colors)
        plt.xlabel(xlabel)
    else:
        colors = palette if palette else sns.color_palette("crest", len(counts))
        ax = plt.bar(counts.index.astype(str), counts.values, color=colors)
        plt.ylabel(xlabel)
        plt.xticks(rotation=25, ha="right")

    plt.title(title, loc="left", fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close()


def make_color_distribution(color_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_color_distribution.png"
    counts = color_df["Color_Family"].replace("", "unknown").value_counts()
    color_map = {
        "black": "#222222",
        "white": "#E8E8E8",
        "gray": "#909090",
        "olive_or_green": "#5D6B3D",
        "khaki_or_beige": "#B8A06A",
        "brown": "#7A5130",
        "blue": "#3E6FA3",
        "red_or_orange": "#C85D3A",
        "yellow": "#D6B84A",
        "purple": "#7E5AA8",
        "unknown": "#CBD2D9",
    }
    palette = [color_map.get(str(name), "#8BA6A9") for name in counts.index]
    save_bar_chart(counts, "Dominant Color Family Distribution", path, palette=palette)
    return path


def make_scene_distribution(feature_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_scene_distribution.png"
    counts = feature_df["Scenario"].replace("", "Unclear").value_counts()
    save_bar_chart(counts, "Scenario Distribution", path)
    return path


def make_fit_distribution(feature_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_fit_distribution.png"
    counts = feature_df["Fit"].replace("", "Unclear").value_counts()
    save_bar_chart(counts, "Fit Distribution", path)
    return path


def make_painpoint_distribution(pain_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_painpoint_distribution.png"
    if pain_df.empty or "Pain_Point" not in pain_df.columns:
        counts = pd.Series({"No data": 1})
    else:
        english_labels = pain_df["Pain_Point"].map(
            lambda value: PAIN_POINT_ENGLISH_LABELS.get(normalize_text(value), normalize_text(value) or "unknown")
        )
        counts = english_labels.value_counts().head(12)
    save_bar_chart(counts, "Pain Point Distribution", path, horizontal=True)
    return path


def make_visual_weight_painpoint(feature_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_visual_weight_painpoint.png"
    rows: List[Dict[str, str]] = []
    for _, row in feature_df.iterrows():
        weight = normalize_text(row.get("Visual_Weight")) or "unclear"
        for pain in split_terms(row.get("Text_Pain_Points")):
            rows.append({"Visual_Weight": weight, "Pain_Point": pain})

    plt.figure(figsize=(8.5, 5.2), dpi=180)
    sns.set_theme(style="whitegrid", font=DEFAULT_FONT_FAMILY)
    if rows:
        relation_df = pd.DataFrame(rows)
        table = pd.crosstab(relation_df["Pain_Point"], relation_df["Visual_Weight"])
        sns.heatmap(table, annot=True, fmt="d", cmap="YlGnBu", cbar=False)
        plt.title("Visual Weight x Pain Point", loc="left", fontweight="bold")
        plt.xlabel("Visual Weight")
        plt.ylabel("Pain Point")
    else:
        plt.text(
            0.5,
            0.55,
            "No matched image-level pain point data",
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
        )
        plt.text(
            0.5,
            0.42,
            "Current Node B coverage is limited; this figure is a demo placeholder.",
            ha="center",
            va="center",
            fontsize=9,
            color="#666666",
        )
        plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def find_chinese_font() -> Optional[str]:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def configure_fonts() -> str:
    font_path = find_chinese_font()
    if font_path:
        font_manager.fontManager.addfont(font_path)
        family = font_manager.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.family"] = family
        plt.rcParams["axes.unicode_minus"] = False
        return family
    plt.rcParams["axes.unicode_minus"] = False
    return "DejaVu Sans"


DEFAULT_FONT_FAMILY = configure_fonts()


def make_wordcloud(word_df: pd.DataFrame, text_feature_df: pd.DataFrame) -> Path:
    path = OUTPUT_DIR / "fig_visual_wordcloud.png"
    frequencies: Dict[str, int] = {}

    if not word_df.empty and {"Word", "Frequency"}.issubset(word_df.columns):
        for _, row in word_df.iterrows():
            word = normalize_text(row.get("Word"))
            if not word or word.isdigit() or len(word) < 2:
                continue
            try:
                freq = int(float(row.get("Frequency", 0)))
            except ValueError:
                freq = 0
            if freq > 0:
                frequencies[word] = freq

    domain_counter: Counter[str] = Counter()
    for column in ["Keywords", "Color_Terms", "Material_Terms", "Function_Terms", "Scenario_Terms"]:
        if column not in text_feature_df.columns:
            continue
        for value in text_feature_df[column].head(5000):
            domain_counter.update(split_terms(value))

    for word, count in domain_counter.items():
        if word and not word.isdigit() and len(word) >= 2:
            frequencies[word] = max(frequencies.get(word, 0), int(count) * 5)

    if not frequencies:
        frequencies = {"Gorpcore": 10, "Outdoor": 8, "Urban": 6}

    try:
        wordcloud = WordCloud(
            width=1400,
            height=800,
            background_color="white",
            font_path=find_chinese_font(),
            max_words=120,
            collocations=False,
            prefer_horizontal=0.88,
        ).generate_from_frequencies(frequencies)
        plt.figure(figsize=(10, 5.8), dpi=180)
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(path, bbox_inches="tight", facecolor="white")
        plt.close()
    except Exception:
        top = pd.Series(frequencies).sort_values(ascending=False).head(20)
        save_bar_chart(top, "Visual Word Cloud Fallback: Top Terms", path, horizontal=True)

    return path


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def main() -> None:
    image_index_df = read_csv(IMAGE_INDEX_CSV)
    quality_df = read_csv(QUALITY_FILTERED_CSV)
    text_feature_df = read_csv(TEXT_FEATURE_CSV)
    pain_df = read_csv(PAIN_POINT_CSV)
    word_df = read_csv(WORD_FREQUENCY_CSV)
    cross_checked_df = read_csv(CROSS_CHECKED_CSV)

    if image_index_df.empty or quality_df.empty:
        raise FileNotFoundError("Required image index or quality filter CSV is missing.")

    quality_df["passed_bool"] = quality_df["passed"].map(normalize_bool)
    passed_df = quality_df[quality_df["passed_bool"]].copy()
    base_df = passed_df.merge(
        image_index_df,
        on=["Image_ID", "note_id"],
        how="left",
        suffixes=("_quality", ""),
    )
    base_df["Source_ID"] = base_df["Image_ID"].map(source_id_from_image_id)
    base_df["local_image_path"] = base_df.apply(resolve_local_image_path, axis=1)

    text_feature_lookup: Dict[str, pd.Series] = {}
    if not text_feature_df.empty and "Source_ID" in text_feature_df.columns:
        for _, row in text_feature_df.iterrows():
            source_id = normalize_text(row.get("Source_ID"))
            if source_id and source_id not in text_feature_lookup:
                text_feature_lookup[source_id] = row

    cross_checked_lookup: Dict[str, pd.Series] = {}
    if not cross_checked_df.empty and "Image_ID" in cross_checked_df.columns:
        for _, row in cross_checked_df.iterrows():
            cross_checked_lookup[normalize_text(row.get("Image_ID"))] = row

    labels = load_json_labels()

    color_rows: List[Dict[str, Any]] = []
    component_rows: List[Dict[str, Any]] = []
    feature_rows: List[Dict[str, Any]] = []

    for _, row in base_df.iterrows():
        image_id = normalize_text(row.get("Image_ID"))
        source_id = normalize_text(row.get("Source_ID"))
        image_path = row.get("local_image_path")
        text_feature = text_feature_lookup.get(source_id)
        label = labels.get(image_id)
        cross_row = cross_checked_lookup.get(image_id)

        color_feature = extract_color_features(image_path)
        color_row = {
            "Image_ID": image_id,
            "note_id": normalize_text(row.get("note_id")),
            "image_path": project_relative(image_path),
            **color_feature,
        }
        color_rows.append(color_row)

        component_row = build_component_row(row, label, text_feature)
        component_rows.append(component_row)

        feature_rows.append(
            {
                "Image_ID": image_id,
                "note_id": normalize_text(row.get("note_id")),
                "Source_ID": source_id,
                "keyword": normalize_text(row.get("keyword")),
                "title_text": normalize_text(row.get("title_text")),
                "raw_text": normalize_text(row.get("raw_text")),
                "publish_time_resolved": normalize_text(row.get("publish_time_resolved")),
                "image_path": project_relative(image_path),
                "Primary_HEX": color_feature["Primary_HEX"],
                "Secondary_HEX": color_feature["Secondary_HEX"],
                "Dominant_Color_Name": color_feature["Dominant_Color_Name"],
                "Color_Family": color_feature["Color_Family"],
                "Pockets": component_row["Pockets"],
                "Zipper_Type": component_row["Zipper_Type"],
                "Drawcord": component_row["Drawcord"],
                "Buckle": component_row["Buckle"],
                "Reflective": component_row["Reflective"],
                "Hood": component_row["Hood"],
                "Fit": component_row["Fit"],
                "Scenario": component_row["Scenario"],
                "Visual_Weight": component_row["Visual_Weight"],
                "Text_Keywords": first_nonempty(
                    text_feature.get("Keywords") if text_feature is not None else "",
                    cross_row.get("Text_Keywords") if cross_row is not None else "",
                ),
                "Text_Pain_Points": first_nonempty(
                    text_feature.get("Pain_Points") if text_feature is not None else "",
                    cross_row.get("Text_Pain_Points") if cross_row is not None else "",
                ),
                "Text_Sentiment": first_nonempty(
                    text_feature.get("Sentiment") if text_feature is not None else "",
                    cross_row.get("Text_Sentiment") if cross_row is not None else "",
                ),
                "Text_Sentiment_Score": first_nonempty(
                    text_feature.get("Sentiment_Score") if text_feature is not None else "",
                    cross_row.get("Text_Sentiment_Score") if cross_row is not None else "",
                ),
                "Text_Color_Terms": first_nonempty(
                    text_feature.get("Color_Terms") if text_feature is not None else "",
                    cross_row.get("Text_Color_Terms") if cross_row is not None else "",
                ),
                "Text_Material_Terms": first_nonempty(
                    text_feature.get("Material_Terms") if text_feature is not None else "",
                    cross_row.get("Text_Material_Terms") if cross_row is not None else "",
                ),
                "Text_Function_Terms": first_nonempty(
                    text_feature.get("Function_Terms") if text_feature is not None else "",
                    cross_row.get("Text_Function_Terms") if cross_row is not None else "",
                ),
                "Text_Scenario_Terms": first_nonempty(
                    text_feature.get("Scenario_Terms") if text_feature is not None else "",
                    cross_row.get("Text_Scenario_Terms") if cross_row is not None else "",
                ),
                "Gorpcore_Relevance": first_nonempty(
                    label.get("Gorpcore_Relevance") if label else "",
                    cross_row.get("Gorpcore_Relevance") if cross_row is not None else "",
                ),
                "Final_Confidence": first_nonempty(
                    cross_row.get("Final_Confidence") if cross_row is not None else "",
                    label.get("Confidence") if label else "",
                    component_row["Component_Confidence"],
                ),
                "Component_Source": component_row["Component_Source"],
                "Component_Confidence": component_row["Component_Confidence"],
                "Color_Extraction_Status": color_feature["Color_Extraction_Status"],
            }
        )

    color_fields = [
        "Image_ID",
        "note_id",
        "image_path",
        "Primary_HEX",
        "Secondary_HEX",
        "Dominant_Color_Name",
        "Color_Family",
        "Primary_Color_Ratio",
        "Secondary_Color_Ratio",
        "Color_Extraction_Status",
    ]
    component_fields = [
        "Image_ID",
        "note_id",
        "Pockets",
        "Zipper_Type",
        "Drawcord",
        "Buckle",
        "Reflective",
        "Hood",
        "Fit",
        "Scenario",
        "Visual_Weight",
        "Component_Source",
        "Component_Confidence",
        "Component_Notes",
    ]
    feature_fields = [
        "Image_ID",
        "note_id",
        "Source_ID",
        "keyword",
        "title_text",
        "raw_text",
        "publish_time_resolved",
        "image_path",
        "Primary_HEX",
        "Secondary_HEX",
        "Dominant_Color_Name",
        "Color_Family",
        "Pockets",
        "Zipper_Type",
        "Drawcord",
        "Buckle",
        "Reflective",
        "Hood",
        "Fit",
        "Scenario",
        "Visual_Weight",
        "Text_Keywords",
        "Text_Pain_Points",
        "Text_Sentiment",
        "Text_Sentiment_Score",
        "Text_Color_Terms",
        "Text_Material_Terms",
        "Text_Function_Terms",
        "Text_Scenario_Terms",
        "Gorpcore_Relevance",
        "Final_Confidence",
        "Component_Source",
        "Component_Confidence",
        "Color_Extraction_Status",
    ]

    write_csv(COLOR_FEATURES_CSV, color_rows, color_fields)
    write_csv(COMPONENT_SUMMARY_CSV, component_rows, component_fields)
    write_csv(FEATURE_DATABASE_CSV, feature_rows, feature_fields)

    color_df = pd.DataFrame(color_rows)
    feature_df = pd.DataFrame(feature_rows)
    figure_paths = [
        make_color_distribution(color_df),
        make_scene_distribution(feature_df),
        make_fit_distribution(feature_df),
        make_painpoint_distribution(pain_df),
        make_visual_weight_painpoint(feature_df),
        make_wordcloud(word_df, text_feature_df),
    ]

    color_status = Counter(row["Color_Extraction_Status"] for row in color_rows)
    component_sources = Counter(row["Component_Source"] for row in component_rows)
    text_matches = sum(1 for row in feature_rows if row["Text_Keywords"] or row["Text_Pain_Points"])

    summary = {
        "module": "Member E - Evidence Fusion and Visual Displays",
        "input_files": {
            "image_index_csv": project_relative(IMAGE_INDEX_CSV),
            "quality_filtered_csv": project_relative(QUALITY_FILTERED_CSV),
            "json_label_dir": project_relative(JSON_LABEL_DIR),
            "text_feature_csv": project_relative(TEXT_FEATURE_CSV),
            "pain_point_csv": project_relative(PAIN_POINT_CSV),
            "word_frequency_csv": project_relative(WORD_FREQUENCY_CSV),
        },
        "input_counts": {
            "image_index_rows": int(len(image_index_df)),
            "quality_rows": int(len(quality_df)),
            "passed_images": int(len(base_df)),
            "node_b_json_labels": int(len(labels)),
            "text_feature_rows": int(len(text_feature_df)),
            "pain_point_rows": int(len(pain_df)),
        },
        "output_counts": {
            "color_features_rows": int(len(color_rows)),
            "component_summary_rows": int(len(component_rows)),
            "feature_database_rows": int(len(feature_rows)),
            "text_matched_image_rows": int(text_matches),
        },
        "color_extraction_status": dict(color_status),
        "component_source_breakdown": dict(component_sources),
        "outputs": {
            "color_features_csv": project_relative(COLOR_FEATURES_CSV),
            "component_summary_csv": project_relative(COMPONENT_SUMMARY_CSV),
            "feature_database_csv": project_relative(FEATURE_DATABASE_CSV),
            "figures": [project_relative(path) for path in figure_paths],
        },
        "limitations": [
            "Node B visual labels currently cover only the available JSON files; full-image component detection is not claimed.",
            "Component fields without visual labels use text heuristics or remain unknown.",
            "Visual weight x pain point is an early-insight/demo chart because image-level visual weight coverage is limited.",
        ],
    }

    with SUMMARY_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Member E evidence fusion completed.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Passed images processed: {len(base_df)}")
    print(f"Color extraction status: {dict(color_status)}")
    print(f"Component sources: {dict(component_sources)}")


if __name__ == "__main__":
    main()
