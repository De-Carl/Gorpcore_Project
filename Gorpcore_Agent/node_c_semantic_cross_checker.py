"""
Node C: Semantic Cross-check.

This node connects visual annotations from Node B with the source text and
text-analysis outputs. Its job is to lower confidence or send records to manual
review when the image label and semantic context disagree.

Inputs:
    Gorpcore_Agent/output/json_labels/*.json
    Dataset/xhs/xiaohongshu_with_images.json
    Gorpcore_Agent/output/quality_filtered_images.csv
    Gorpcore_Agent/output/text_analysis/*.csv
    Gorpcore_Agent/member_d_text_analysis/output/text_analysis/*.csv

Outputs:
    Gorpcore_Agent/output/cross_checked_records.csv
    Gorpcore_Agent/output/review_pool.csv
    Gorpcore_Agent/output/semantic_cross_check_log.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from config import (
    CROSS_CHECKED_RECORDS_CSV,
    JSON_LABEL_DIR,
    LEGACY_TEXT_ANALYSIS_OUTPUT_DIR,
    QUALITY_FILTERED_CSV,
    RAW_DATA_JSON,
    SEMANTIC_CROSS_CHECK_LOG_JSON,
    SEMANTIC_REVIEW_POOL_CSV,
    TEXT_ANALYSIS_OUTPUT_DIR,
    ensure_output_dirs,
)
from data_loader import load_image_records


# ============================================================
# Output schema
# ============================================================

CROSS_CHECK_FIELDNAMES = [
    "Image_ID",
    "note_id",
    "image_path",
    "keyword",
    "Source_ID",
    "Source_Text",
    "Curation_Status",
    "Image_Category",
    "Primary_Color",
    "Secondary_Color",
    "Material_Clue",
    "Scenario",
    "Visual_Weight",
    "Pockets",
    "Zipper_Type",
    "Fit",
    "Reflective",
    "Text_Keywords",
    "Text_Pain_Points",
    "Text_Sentiment",
    "Text_Sentiment_Score",
    "Text_Color_Terms",
    "Text_Material_Terms",
    "Text_Function_Terms",
    "Text_Scenario_Terms",
    "Semantic_Consistency_Score",
    "Conflict_Type",
    "Conflict_Reason",
    "Useful_Design_Signal",
    "Gorpcore_Relevance",
    "Visual_Confidence",
    "Final_Confidence",
    "Review_Needed",
    "Review_Reason",
]

REVIEW_POOL_FIELDNAMES = CROSS_CHECK_FIELDNAMES + [
    "Reviewer",
    "Manual_Decision",
    "Manual_Category",
    "Manual_Notes",
    "Corrected_Color",
    "Corrected_Material",
    "Corrected_Scenario",
    "Corrected_Pain_Point",
    "Reviewed_At",
]


# ============================================================
# Semantic rule dictionaries
# ============================================================

SUMMER_TERMS = {
    "夏天",
    "夏季",
    "夏日",
    "炎热",
    "热天",
    "spring",
    "summer",
}

LIGHTWEIGHT_TERMS = {
    "轻薄",
    "轻量",
    "轻便",
    "薄款",
    "不闷",
    "透气",
    "light",
    "lightweight",
    "breathable",
}

COMMUTE_TERMS = {
    "通勤",
    "上班",
    "日常",
    "城市",
    "city",
    "urban",
    "commute",
    "office",
}

OUTDOOR_TERMS = {
    "户外",
    "徒步",
    "登山",
    "露营",
    "越野",
    "山系",
    "outdoor",
    "hiking",
    "trail",
    "camping",
}

HEAVY_MATERIAL_TERMS = {
    "fleece",
    "down",
    "insulated",
    "padding",
    "padded",
    "heavy",
    "thick",
    "wool",
    "composite fleece",
    "羽绒",
    "抓绒",
    "厚",
    "保暖",
}

SHELL_MATERIAL_TERMS = {
    "shell",
    "hard shell",
    "hardshell",
    "waterproof",
    "gore-tex",
    "gore tex",
    "membrane",
    "sealed",
    "防水",
    "硬壳",
    "冲锋衣",
    "压胶",
}

COLOR_MAP = {
    "黑": {"black"},
    "白": {"white"},
    "白色": {"white"},
    "灰": {"gray", "grey"},
    "蓝": {"blue", "navy"},
    "藏青": {"navy", "blue"},
    "军绿": {"olive", "green", "army green"},
    "橄榄绿": {"olive", "green"},
    "卡其": {"khaki", "tan", "beige"},
    "红": {"red"},
    "黄": {"yellow"},
    "橙": {"orange"},
}


# ============================================================
# Generic utilities
# ============================================================

def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def clamp_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def split_terms(value: Any) -> List[str]:
    text = safe_text(value)
    if not text:
        return []
    parts = [part.strip() for part in text.replace(";", "|").split("|")]
    return [part for part in parts if part]


def join_terms(values: Iterable[str]) -> str:
    cleaned = [safe_text(value) for value in values if safe_text(value)]
    return " | ".join(dict.fromkeys(cleaned))


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


# ============================================================
# Input loaders
# ============================================================

def resolve_text_analysis_dir() -> Optional[Path]:
    canonical_feature = TEXT_ANALYSIS_OUTPUT_DIR / "text_feature_vectors.csv"
    legacy_feature = LEGACY_TEXT_ANALYSIS_OUTPUT_DIR / "text_feature_vectors.csv"

    if canonical_feature.exists():
        return TEXT_ANALYSIS_OUTPUT_DIR
    if legacy_feature.exists():
        return LEGACY_TEXT_ANALYSIS_OUTPUT_DIR
    return None


def load_visual_labels(label_dir: Path = JSON_LABEL_DIR) -> List[Dict[str, Any]]:
    if not label_dir.exists():
        raise FileNotFoundError(
            f"Cannot find Node B JSON label directory: {label_dir}. "
            "Please run node_b_vision_annotator.py first."
        )

    labels: List[Dict[str, Any]] = []
    for path in sorted(label_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                label = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            labels.append(
                {
                    "Image_ID": path.stem,
                    "label_load_error": str(e),
                    "Confidence": 0.0,
                    "Gorpcore_Relevance": 0.0,
                }
            )
            continue

        label.setdefault("Image_ID", path.stem)
        labels.append(label)

    if not labels:
        raise FileNotFoundError(
            f"No JSON labels found in {label_dir}. Please run Node B first."
        )

    return labels


def load_image_context_by_id() -> Dict[str, Dict[str, Any]]:
    return {record["Image_ID"]: record for record in load_image_records(save_index=False)}


def load_quality_records() -> Dict[str, Dict[str, str]]:
    return {row.get("Image_ID", ""): row for row in read_csv_rows(QUALITY_FILTERED_CSV)}


def load_text_features() -> Tuple[Dict[str, Dict[str, str]], Dict[str, List[Dict[str, str]]], str]:
    text_dir = resolve_text_analysis_dir()
    if text_dir is None:
        return {}, {}, "not_found"

    feature_rows = read_csv_rows(text_dir / "text_feature_vectors.csv")
    pain_rows = read_csv_rows(text_dir / "pain_point_table.csv")

    features_by_source = {
        row.get("Source_ID", ""): row
        for row in feature_rows
        if row.get("Source_ID", "")
    }
    pain_by_source: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in pain_rows:
        source_id = row.get("Source_ID", "")
        if source_id:
            pain_by_source[source_id].append(row)

    return features_by_source, pain_by_source, str(text_dir)


def load_raw_note_texts() -> Dict[str, str]:
    if not RAW_DATA_JSON.exists():
        return {}
    with RAW_DATA_JSON.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)
    if not isinstance(raw_data, list):
        return {}

    note_texts: Dict[str, str] = {}
    for note in raw_data:
        note_id = safe_text(note.get("note_id"))
        title = safe_text(note.get("title_text"))
        body = safe_text(note.get("raw_text"))
        parts = [part for part in (title, body) if part]
        if note_id and parts:
            note_texts[note_id] = "\n".join(dict.fromkeys(parts))
    return note_texts


# ============================================================
# Label and text normalization
# ============================================================

def infer_curation_status(label: Dict[str, Any]) -> str:
    status = safe_text(label.get("Curation_Status"))
    if status:
        return status

    relevance = clamp_float(label.get("Gorpcore_Relevance"), default=0.0)
    primary = safe_text(label.get("Primary_Color")).lower()
    material = " ".join(normalize_material_clue(label)).lower()

    if relevance >= 0.45:
        return "use"
    if primary in {"", "none", "unclear"} and material in {"", "unclear"}:
        return "review"
    return "review"


def normalize_material_clue(label: Dict[str, Any]) -> List[str]:
    value = label.get("Material_Clue", [])
    if isinstance(value, list):
        materials = [safe_text(item) for item in value if safe_text(item)]
    elif safe_text(value):
        materials = [safe_text(value)]
    else:
        materials = []
    return materials or ["unclear"]


def source_id_from_note_id(note_id: str) -> str:
    return f"GRP-XHS-{note_id}" if note_id else ""


def build_source_text(
    label: Dict[str, Any],
    image_context: Dict[str, Any],
    note_texts: Dict[str, str],
    text_feature: Optional[Dict[str, str]],
) -> str:
    if text_feature and safe_text(text_feature.get("Cleaned_Text")):
        return safe_text(text_feature.get("Cleaned_Text"))

    note_id = safe_text(label.get("note_id") or image_context.get("note_id"))
    if note_id and note_id in note_texts:
        return note_texts[note_id]

    title = safe_text(image_context.get("title_text"))
    body = safe_text(image_context.get("raw_text"))
    return "\n".join(part for part in (title, body) if part)


def collect_text_pain_points(
    text_feature: Optional[Dict[str, str]],
    pain_rows: Sequence[Dict[str, str]],
) -> List[str]:
    pain_points = split_terms(text_feature.get("Pain_Points") if text_feature else "")
    pain_points.extend(row.get("Pain_Point", "") for row in pain_rows)
    return [pain for pain in dict.fromkeys(pain_points) if pain]


def text_color_matches_visual(text_color_terms: Sequence[str], primary_color: str) -> bool:
    if not text_color_terms or not primary_color:
        return True

    visual = primary_color.lower()
    expected_colors: List[str] = []
    for term in text_color_terms:
        expected_colors.extend(COLOR_MAP.get(term, {term.lower()}))

    return any(expected in visual for expected in expected_colors)


# ============================================================
# Cross-check rules
# ============================================================

def evaluate_record(
    label: Dict[str, Any],
    image_context: Dict[str, Any],
    quality_record: Dict[str, str],
    text_feature: Optional[Dict[str, str]],
    pain_rows: Sequence[Dict[str, str]],
    source_text: str,
) -> Dict[str, Any]:
    image_id = safe_text(label.get("Image_ID"))
    note_id = safe_text(label.get("note_id") or image_context.get("note_id"))
    source_id = source_id_from_note_id(note_id)

    curation_status = infer_curation_status(label)
    image_category = safe_text(label.get("Image_Category")) or "unclear"
    primary_color = safe_text(label.get("Primary_Color")) or "unclear"
    secondary_color = safe_text(label.get("Secondary_Color")) or "none"
    materials = normalize_material_clue(label)
    material_text = " ".join(materials).lower()
    scenario = safe_text(label.get("Scenario")) or "Unclear"
    visual_weight = safe_text(label.get("Visual_Weight")) or "unclear"
    visual_weight_lower = visual_weight.lower()
    text_lower = source_text.lower()

    text_keywords = split_terms(text_feature.get("Keywords") if text_feature else "")
    text_color_terms = split_terms(text_feature.get("Color_Terms") if text_feature else "")
    text_material_terms = split_terms(text_feature.get("Material_Terms") if text_feature else "")
    text_function_terms = split_terms(text_feature.get("Function_Terms") if text_feature else "")
    text_scenario_terms = split_terms(text_feature.get("Scenario_Terms") if text_feature else "")
    text_pain_points = collect_text_pain_points(text_feature, pain_rows)
    text_sentiment = safe_text(text_feature.get("Sentiment") if text_feature else "")
    text_sentiment_score = safe_text(text_feature.get("Sentiment_Score") if text_feature else "")

    visual_confidence = clamp_float(label.get("Confidence"), default=0.0)
    relevance = clamp_float(label.get("Gorpcore_Relevance"), default=0.0)

    penalties: List[float] = []
    conflicts: List[str] = []
    conflict_reasons: List[str] = []
    design_signals: List[str] = []
    review_reasons: List[str] = []

    has_text = bool(source_text.strip())
    if not has_text:
        penalties.append(0.20)
        conflicts.append("missing_text_context")
        conflict_reasons.append("No source text or text-analysis record was found.")
        review_reasons.append("missing_text_context")

    if label.get("label_load_error"):
        penalties.append(0.50)
        conflicts.append("label_load_error")
        conflict_reasons.append(safe_text(label.get("label_load_error")))
        review_reasons.append("label_load_error")

    if curation_status == "reject" or image_category in {
        "landscape",
        "text_screenshot",
        "unrelated",
    }:
        penalties.append(0.25)
        conflicts.append("visual_rejected_or_non_outfit")
        conflict_reasons.append(
            f"Node B status/category is {curation_status}/{image_category}."
        )
        review_reasons.append("visual_rejected_or_non_outfit")

    if visual_confidence < 0.65:
        penalties.append(0.15)
        review_reasons.append("low_visual_confidence")

    if relevance < 0.35 and curation_status != "reject":
        penalties.append(0.12)
        review_reasons.append("low_gorpcore_relevance")

    if quality_record and safe_text(quality_record.get("passed")).lower() != "true":
        penalties.append(0.30)
        conflicts.append("node_a_rejected_but_label_exists")
        conflict_reasons.append(
            f"Node A marked this image as {quality_record.get('image_type', '')}."
        )
        review_reasons.append("node_a_rejected_but_label_exists")

    text_claims_summer_light = (
        contains_any(text_lower, SUMMER_TERMS)
        or contains_any(text_lower, LIGHTWEIGHT_TERMS)
        or any(term in {"轻量", "透气"} for term in text_function_terms)
    )
    visual_is_heavy = (
        visual_weight_lower == "heavyweight"
        or contains_any(material_text, HEAVY_MATERIAL_TERMS)
    )
    visual_is_shell = contains_any(material_text, SHELL_MATERIAL_TERMS)

    if text_claims_summer_light and visual_is_heavy:
        penalties.append(0.22)
        conflicts.append("summer_lightweight_text_vs_heavy_visual")
        conflict_reasons.append(
            "Text suggests summer/lightweight/breathable use, but visual label suggests heavy material."
        )
        review_reasons.append("summer_lightweight_text_vs_heavy_visual")

    if contains_any(text_lower, COMMUTE_TERMS) and scenario in {"Outdoor", "Sports"}:
        penalties.append(0.10)
        conflicts.append("commute_text_vs_outdoor_visual")
        conflict_reasons.append(
            f"Text indicates commute/daily use, while visual scenario is {scenario}."
        )

    if (
        contains_any(text_lower, OUTDOOR_TERMS)
        and scenario in {"Urban_Commute", "Office", "Fashion_Street"}
        and relevance < 0.55
    ):
        penalties.append(0.10)
        conflicts.append("outdoor_text_vs_low_relevance_urban_visual")
        conflict_reasons.append(
            "Text indicates outdoor use, but visual label is urban/low-relevance."
        )

    if "不透气" in text_pain_points and (visual_is_shell or visual_weight_lower in {"medium", "heavyweight"}):
        design_signals.append("breathability_risk_supported_by_shell_or_weight")

    if "太重" in text_pain_points and visual_weight_lower in {"medium", "heavyweight"}:
        design_signals.append("weight_risk_supported_by_visual_weight")

    if "拉链问题" in text_pain_points and safe_text(label.get("Zipper_Type")) not in {"None", "Unclear", ""}:
        design_signals.append("zipper_pain_point_matches_visible_zipper")

    if "版型差" in text_pain_points and safe_text(label.get("Fit")) not in {"Unclear", ""}:
        design_signals.append("fit_pain_point_matches_visible_fit")

    if "不适合通勤" in text_pain_points and scenario == "Urban_Commute":
        penalties.append(0.12)
        conflicts.append("commute_visual_vs_commute_pain_point")
        conflict_reasons.append(
            "Visual scenario is Urban_Commute, but text pain point says it is not commute-friendly."
        )
        review_reasons.append("commute_visual_vs_commute_pain_point")

    if not text_color_matches_visual(text_color_terms, primary_color):
        penalties.append(0.08)
        conflicts.append("color_text_visual_mismatch")
        conflict_reasons.append(
            f"Text color terms ({join_terms(text_color_terms)}) do not match primary color ({primary_color})."
        )

    if safe_text(label.get("Text_Overlay_Level")).lower() == "high":
        penalties.append(0.10)
        review_reasons.append("high_text_overlay")

    support_bonus = min(len(design_signals) * 0.03, 0.09)
    total_penalty = min(sum(penalties), 0.75)
    semantic_score = max(0.0, min(1.0, 1.0 - total_penalty + support_bonus))
    final_confidence = max(0.0, min(1.0, visual_confidence * semantic_score))

    review_needed = (
        bool(review_reasons)
        or final_confidence < 0.70
        or semantic_score < 0.72
        or curation_status == "review"
    )
    if final_confidence < 0.70:
        review_reasons.append("final_confidence_below_0.70")
    if semantic_score < 0.72:
        review_reasons.append("semantic_consistency_below_0.72")
    if curation_status == "review":
        review_reasons.append("node_b_review_status")

    return {
        "Image_ID": image_id,
        "note_id": note_id,
        "image_path": safe_text(label.get("image_path") or image_context.get("image_path")),
        "keyword": safe_text(image_context.get("keyword")),
        "Source_ID": source_id,
        "Source_Text": source_text,
        "Curation_Status": curation_status,
        "Image_Category": image_category,
        "Primary_Color": primary_color,
        "Secondary_Color": secondary_color,
        "Material_Clue": join_terms(materials),
        "Scenario": scenario,
        "Visual_Weight": visual_weight,
        "Pockets": safe_int(label.get("Pockets"), default=0),
        "Zipper_Type": safe_text(label.get("Zipper_Type")) or "Unclear",
        "Fit": safe_text(label.get("Fit")) or "Unclear",
        "Reflective": safe_text(label.get("Reflective")),
        "Text_Keywords": join_terms(text_keywords),
        "Text_Pain_Points": join_terms(text_pain_points),
        "Text_Sentiment": text_sentiment,
        "Text_Sentiment_Score": text_sentiment_score,
        "Text_Color_Terms": join_terms(text_color_terms),
        "Text_Material_Terms": join_terms(text_material_terms),
        "Text_Function_Terms": join_terms(text_function_terms),
        "Text_Scenario_Terms": join_terms(text_scenario_terms),
        "Semantic_Consistency_Score": round(semantic_score, 4),
        "Conflict_Type": join_terms(conflicts) or "none",
        "Conflict_Reason": join_terms(conflict_reasons) or "none",
        "Useful_Design_Signal": join_terms(design_signals) or "none",
        "Gorpcore_Relevance": round(relevance, 4),
        "Visual_Confidence": round(visual_confidence, 4),
        "Final_Confidence": round(final_confidence, 4),
        "Review_Needed": review_needed,
        "Review_Reason": join_terms(review_reasons) or "none",
    }


# ============================================================
# Reporting
# ============================================================

def build_review_pool_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    review_rows: List[Dict[str, Any]] = []
    for row in rows:
        if safe_text(row.get("Review_Needed")).lower() != "true":
            continue
        review_row = dict(row)
        review_row.update(
            {
                "Reviewer": "",
                "Manual_Decision": "",
                "Manual_Category": "",
                "Manual_Notes": "",
                "Corrected_Color": "",
                "Corrected_Material": "",
                "Corrected_Scenario": "",
                "Corrected_Pain_Point": "",
                "Reviewed_At": "",
            }
        )
        review_rows.append(review_row)
    return review_rows


def save_cross_check_log(
    rows: Sequence[Dict[str, Any]],
    review_rows: Sequence[Dict[str, Any]],
    text_source: str,
) -> None:
    conflict_counter = Counter()
    signal_counter = Counter()
    status_counter = Counter()
    category_counter = Counter()

    for row in rows:
        status_counter[safe_text(row.get("Curation_Status")) or "unknown"] += 1
        category_counter[safe_text(row.get("Image_Category")) or "unknown"] += 1
        for conflict in split_terms(row.get("Conflict_Type")):
            conflict_counter[conflict] += 1
        for signal in split_terms(row.get("Useful_Design_Signal")):
            signal_counter[signal] += 1

    log_data = {
        "node": "Node C - Semantic Cross-check",
        "description": (
            "Cross-check Node B visual labels against XHS source text and text-analysis outputs. "
            "Rows with low confidence or semantic conflict are exported to the manual review pool."
        ),
        "total_visual_labels": len(rows),
        "review_pool_count": len(review_rows),
        "text_analysis_source": text_source,
        "curation_status_breakdown": dict(status_counter),
        "image_category_breakdown": dict(category_counter),
        "conflict_type_breakdown": dict(conflict_counter),
        "useful_design_signal_breakdown": dict(signal_counter),
        "cross_checked_records_csv": str(CROSS_CHECKED_RECORDS_CSV),
        "review_pool_csv": str(SEMANTIC_REVIEW_POOL_CSV),
    }

    with SEMANTIC_CROSS_CHECK_LOG_JSON.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


# ============================================================
# Main process
# ============================================================

def run_semantic_cross_checker() -> Dict[str, Any]:
    ensure_output_dirs()

    visual_labels = load_visual_labels()
    image_context_by_id = load_image_context_by_id()
    quality_by_id = load_quality_records()
    text_features_by_source, pain_by_source, text_source = load_text_features()
    note_texts = load_raw_note_texts()

    cross_checked_rows: List[Dict[str, Any]] = []

    for label in visual_labels:
        image_id = safe_text(label.get("Image_ID"))
        image_context = image_context_by_id.get(image_id, {})
        note_id = safe_text(label.get("note_id") or image_context.get("note_id"))
        source_id = source_id_from_note_id(note_id)
        text_feature = text_features_by_source.get(source_id)
        pain_rows = pain_by_source.get(source_id, [])
        source_text = build_source_text(label, image_context, note_texts, text_feature)
        quality_record = quality_by_id.get(image_id, {})

        row = evaluate_record(
            label=label,
            image_context=image_context,
            quality_record=quality_record,
            text_feature=text_feature,
            pain_rows=pain_rows,
            source_text=source_text,
        )
        cross_checked_rows.append(row)

    review_rows = build_review_pool_rows(cross_checked_rows)

    write_csv(CROSS_CHECKED_RECORDS_CSV, CROSS_CHECK_FIELDNAMES, cross_checked_rows)
    write_csv(SEMANTIC_REVIEW_POOL_CSV, REVIEW_POOL_FIELDNAMES, review_rows)
    save_cross_check_log(cross_checked_rows, review_rows, text_source)

    return {
        "total_visual_labels": len(visual_labels),
        "cross_checked_records": len(cross_checked_rows),
        "review_pool_count": len(review_rows),
        "text_analysis_source": text_source,
        "cross_checked_csv": str(CROSS_CHECKED_RECORDS_CSV),
        "review_pool_csv": str(SEMANTIC_REVIEW_POOL_CSV),
        "log_json": str(SEMANTIC_CROSS_CHECK_LOG_JSON),
    }


def main() -> None:
    print("Node C semantic cross-check started...")
    summary = run_semantic_cross_checker()
    print(f"Visual labels: {summary['total_visual_labels']}")
    print(f"Cross-checked records: {summary['cross_checked_records']}")
    print(f"Review pool records: {summary['review_pool_count']}")
    print(f"Text analysis source: {summary['text_analysis_source']}")
    print(f"Cross-check CSV: {summary['cross_checked_csv']}")
    print(f"Review pool CSV: {summary['review_pool_csv']}")
    print(f"Log JSON: {summary['log_json']}")
    print("Node C semantic cross-check completed.")


if __name__ == "__main__":
    main()
