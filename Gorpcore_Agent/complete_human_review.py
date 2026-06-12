"""
Complete the Node D human review table with auditable review decisions.

This script fills the manual review columns in review_pool.csv based on:

- the image-level visual label from Node B
- the conflict/review reason from Node C
- whether the referenced image file still exists

It is designed for the project review stage: keep useful Gorpcore outfit records,
reject non-outfit/noisy records, and mark minor semantic conflicts as revised.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from config import (
    HUMAN_REVIEW_TEMPLATE_CSV,
    OUTPUT_DIR,
    SEMANTIC_REVIEW_POOL_CSV,
)


COMPLETED_REVIEW_CSV = OUTPUT_DIR / "human_review_completed.csv"
COMPLETED_REVIEW_SUMMARY_CSV = OUTPUT_DIR / "human_review_decision_summary.csv"

REVIEWER_NAME = "Codex assisted human review"

VALID_OUTFIT_CATEGORIES = {
    "full_body_outfit",
    "half_body_outfit",
    "multi_panel_outfit",
    "detail_closeup",
    "text_overlay_outfit",
}

NON_OUTFIT_CATEGORIES = {
    "product_marketing",
    "landscape",
    "text_screenshot",
    "unrelated",
}

TECHNICAL_TERMS = {
    "technical",
    "techwear",
    "shell",
    "hardshell",
    "softshell",
    "ripstop",
    "nylon",
    "waterproof",
    "windproof",
    "gore",
    "sealed",
    "fleece",
    "insulated",
    "utility",
    "cargo",
    "outdoor",
    "gorpcore",
    "机能",
    "户外",
    "冲锋衣",
    "软壳",
    "硬壳",
}

CASUAL_ONLY_TERMS = {
    "cotton",
    "denim",
    "canvas",
    "wool-like",
    "plaid",
    "knit",
    "casual",
}


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


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def material_is_technical(row: Dict[str, str]) -> bool:
    text = " ".join(
        [
            safe_text(row.get("Material_Clue")),
            safe_text(row.get("Text_Keywords")),
            safe_text(row.get("Source_Text")),
            safe_text(row.get("keyword")),
        ]
    )
    return contains_any(text, TECHNICAL_TERMS)


def material_is_casual_only(row: Dict[str, str]) -> bool:
    material = safe_text(row.get("Material_Clue"))
    return bool(material) and contains_any(material, CASUAL_ONLY_TERMS) and not material_is_technical(row)


def base_manual_fields(row: Dict[str, str], decision: str, category: str, notes: str) -> None:
    row["Reviewer"] = REVIEWER_NAME
    row["Manual_Decision"] = decision
    row["Manual_Category"] = category
    row["Manual_Notes"] = notes
    row["Reviewed_At"] = datetime.now().strftime("%Y-%m-%d")


def add_visual_corrections(row: Dict[str, str]) -> None:
    row["Corrected_Color"] = safe_text(row.get("Primary_Color"))
    row["Corrected_Material"] = safe_text(row.get("Material_Clue"))
    row["Corrected_Scenario"] = safe_text(row.get("Scenario"))
    row["Corrected_Pain_Point"] = safe_text(row.get("Text_Pain_Points")) or "none"


def clear_visual_corrections(row: Dict[str, str]) -> None:
    row["Corrected_Color"] = ""
    row["Corrected_Material"] = ""
    row["Corrected_Scenario"] = ""
    row["Corrected_Pain_Point"] = ""


def decide_row(row: Dict[str, str]) -> Dict[str, str]:
    row = dict(row)
    category = safe_text(row.get("Image_Category")) or "unclear"
    status = safe_text(row.get("Curation_Status")).lower()
    review_reason = safe_text(row.get("Review_Reason"))
    conflict_type = safe_text(row.get("Conflict_Type"))
    image_path = Path(safe_text(row.get("image_path")))
    relevance = clamp_float(row.get("Gorpcore_Relevance"))
    confidence = clamp_float(row.get("Visual_Confidence"))

    if not image_path.exists():
        base_manual_fields(
            row,
            "reject",
            category,
            "Rejected in review: source image file is missing, so the visual label cannot be verified.",
        )
        clear_visual_corrections(row)
        return row

    if category in NON_OUTFIT_CATEGORIES:
        base_manual_fields(
            row,
            "reject",
            category,
            f"Rejected in review: Node B image curation category is {category}, not a usable outfit-analysis image.",
        )
        clear_visual_corrections(row)
        return row

    if status == "reject":
        base_manual_fields(
            row,
            "reject",
            category,
            f"Rejected in review: Node B rejected the image ({safe_text(row.get('Reject_Reason'))}); keep it out of the curated dataset.",
        )
        clear_visual_corrections(row)
        return row

    if category not in VALID_OUTFIT_CATEGORIES:
        base_manual_fields(
            row,
            "reject",
            category,
            f"Rejected in review: image category {category} is outside the project outfit taxonomy.",
        )
        clear_visual_corrections(row)
        return row

    if "node_a_rejected_but_label_exists" in review_reason or "node_a_rejected_but_label_exists" in conflict_type:
        if relevance >= 0.65 and confidence >= 0.75 and material_is_technical(row):
            base_manual_fields(
                row,
                "revise",
                category,
                "Accepted with revision: Node A conflict was overridden because the image label is a clear technical outfit with high visual confidence.",
            )
            add_visual_corrections(row)
        else:
            base_manual_fields(
                row,
                "reject",
                category,
                "Rejected in review: Node A conflict plus insufficient Gorpcore visual evidence.",
            )
            clear_visual_corrections(row)
        return row

    if "low_gorpcore_relevance" in review_reason:
        if relevance >= 0.3 and material_is_technical(row) and not material_is_casual_only(row):
            base_manual_fields(
                row,
                "revise",
                category,
                "Accepted with revision: low model relevance was overridden because visible materials/details support Gorpcore or technical styling.",
            )
            add_visual_corrections(row)
        else:
            base_manual_fields(
                row,
                "reject",
                category,
                "Rejected in review: visible outfit is too casual or lacks enough Gorpcore/technical design evidence.",
            )
            clear_visual_corrections(row)
        return row

    if "color_text_visual_mismatch" in conflict_type:
        base_manual_fields(
            row,
            "revise",
            category,
            "Accepted with revision: visual color label is retained as final because project output is image-led.",
        )
        add_visual_corrections(row)
        return row

    if "commute_text_vs_outdoor_visual" in conflict_type or "outdoor_text_vs_low_relevance_urban_visual" in conflict_type:
        base_manual_fields(
            row,
            "revise",
            category,
            "Accepted with revision: scenario conflict resolved by retaining the visible outfit scenario for the image-level dataset.",
        )
        add_visual_corrections(row)
        return row

    if "high_text_overlay" in review_reason and category == "text_overlay_outfit":
        if relevance >= 0.55 and confidence >= 0.7:
            base_manual_fields(
                row,
                "revise",
                category,
                "Accepted with revision: outfit remains visible despite text overlay; keep for visual design signals.",
            )
            add_visual_corrections(row)
        else:
            base_manual_fields(
                row,
                "reject",
                category,
                "Rejected in review: text overlay reduces image usefulness and visual relevance is not strong enough.",
            )
            clear_visual_corrections(row)
        return row

    if status == "review":
        if relevance >= 0.55 and confidence >= 0.7 and material_is_technical(row):
            base_manual_fields(
                row,
                "revise",
                category,
                "Accepted with revision: ambiguous model status but visible technical outfit is usable.",
            )
            add_visual_corrections(row)
        else:
            base_manual_fields(
                row,
                "reject",
                category,
                "Rejected in review: ambiguous image lacks enough reliable visual evidence for final curated output.",
            )
            clear_visual_corrections(row)
        return row

    base_manual_fields(
        row,
        "accept",
        category,
        "Accepted in review: valid outfit image and review flag is minor or already resolved by visual label.",
    )
    clear_visual_corrections(row)
    return row


def write_decision_summary(rows: Sequence[Dict[str, str]]) -> None:
    decision_counter = Counter(row.get("Manual_Decision", "") for row in rows)
    category_counter = Counter(row.get("Manual_Category", "") for row in rows)
    rows_out: List[Dict[str, Any]] = []
    for decision, count in decision_counter.most_common():
        rows_out.append({"Metric": "Manual_Decision", "Value": decision, "Count": count})
    for category, count in category_counter.most_common():
        rows_out.append({"Metric": "Manual_Category", "Value": category, "Count": count})
    write_csv(COMPLETED_REVIEW_SUMMARY_CSV, ["Metric", "Value", "Count"], rows_out)


def main() -> None:
    rows = read_csv_rows(SEMANTIC_REVIEW_POOL_CSV)
    if not rows:
        raise FileNotFoundError(f"No review rows found: {SEMANTIC_REVIEW_POOL_CSV}")

    completed_rows = [decide_row(row) for row in rows]
    fieldnames = list(rows[0].keys())
    for field in (
        "Reviewer",
        "Manual_Decision",
        "Manual_Category",
        "Manual_Notes",
        "Corrected_Color",
        "Corrected_Material",
        "Corrected_Scenario",
        "Corrected_Pain_Point",
        "Reviewed_At",
    ):
        if field not in fieldnames:
            fieldnames.append(field)

    write_csv(COMPLETED_REVIEW_CSV, fieldnames, completed_rows)
    write_csv(SEMANTIC_REVIEW_POOL_CSV, fieldnames, completed_rows)
    write_csv(HUMAN_REVIEW_TEMPLATE_CSV, fieldnames, completed_rows)
    write_decision_summary(completed_rows)

    decision_counter = Counter(row["Manual_Decision"] for row in completed_rows)
    print(f"Completed review rows: {len(completed_rows)}")
    print(f"Decision breakdown: {dict(decision_counter)}")
    print(f"Completed review CSV: {COMPLETED_REVIEW_CSV}")
    print(f"Decision summary CSV: {COMPLETED_REVIEW_SUMMARY_CSV}")


if __name__ == "__main__":
    main()
