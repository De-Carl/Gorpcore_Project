"""
Node D: Human Review Consolidator.

Node D is the manual review stage after Node A/B/C:

1. Read Node C cross-checked records.
2. Read the review pool that contains manually editable columns.
3. Apply manual decisions and corrections.
4. Export reviewed records, pending records, final curated records, and a run log.

This node does not replace human judgment. It makes human judgment auditable and
machine-readable, so the final output can clearly separate:

- auto accepted records that do not need review
- manually accepted/revised records
- manually rejected records
- records still pending review

Manual reviewers should fill the existing columns in review_pool.csv:

- Reviewer
- Manual_Decision
- Manual_Category
- Manual_Notes
- Corrected_Color
- Corrected_Material
- Corrected_Scenario
- Corrected_Pain_Point
- Reviewed_At
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from config import (
    CROSS_CHECKED_RECORDS_CSV,
    FINAL_CURATED_RECORDS_CSV,
    HUMAN_REVIEW_LOG_JSON,
    HUMAN_REVIEW_PENDING_CSV,
    HUMAN_REVIEW_TEMPLATE_CSV,
    HUMAN_REVIEWED_RECORDS_CSV,
    SEMANTIC_REVIEW_POOL_CSV,
    ensure_output_dirs,
)


# ============================================================
# Manual review schema
# ============================================================

MANUAL_REVIEW_FIELDS = [
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

NODE_D_FIELDS = [
    "NodeD_Review_Status",
    "NodeD_Decision",
    "NodeD_Reviewer",
    "NodeD_Reviewed_At",
    "NodeD_Notes",
    "Final_Curation_Status",
    "Final_Image_Category",
    "Final_Primary_Color",
    "Final_Material_Clue",
    "Final_Scenario",
    "Final_Pain_Point",
    "Reviewed_Final_Confidence",
]

ACCEPT_DECISIONS = {
    "accept",
    "accepted",
    "approve",
    "approved",
    "keep",
    "use",
    "pass",
    "通过",
    "保留",
    "采用",
}

REJECT_DECISIONS = {
    "reject",
    "rejected",
    "drop",
    "remove",
    "discard",
    "fail",
    "否决",
    "拒绝",
    "删除",
    "剔除",
}

REVISE_DECISIONS = {
    "revise",
    "revised",
    "correct",
    "corrected",
    "modify",
    "modified",
    "update",
    "updated",
    "修正",
    "修改",
    "更正",
}

PENDING_DECISIONS = {
    "",
    "pending",
    "review",
    "needs_review",
    "need_review",
    "待复核",
    "待审核",
}


# ============================================================
# Generic CSV helpers
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


def ordered_fieldnames(*groups: Iterable[str]) -> List[str]:
    fieldnames: List[str] = []
    for group in groups:
        for field in group:
            if field not in fieldnames:
                fieldnames.append(field)
    return fieldnames


def parse_bool(value: Any) -> bool:
    return safe_text(value).lower() in {"true", "1", "yes", "y", "是"}


# ============================================================
# Manual decision normalization
# ============================================================

def normalize_manual_decision(value: Any) -> str:
    decision = safe_text(value).lower()
    if decision in ACCEPT_DECISIONS:
        return "accept"
    if decision in REJECT_DECISIONS:
        return "reject"
    if decision in REVISE_DECISIONS:
        return "revise"
    if decision in PENDING_DECISIONS:
        return "pending"
    return "unknown"


def has_manual_correction(review_row: Dict[str, str]) -> bool:
    return any(
        safe_text(review_row.get(field))
        for field in (
            "Manual_Category",
            "Corrected_Color",
            "Corrected_Material",
            "Corrected_Scenario",
            "Corrected_Pain_Point",
        )
    )


def is_review_row_filled(review_row: Dict[str, str]) -> bool:
    decision = normalize_manual_decision(review_row.get("Manual_Decision"))
    return decision not in {"pending", "unknown"} or has_manual_correction(review_row)


def index_review_rows(review_rows: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    indexed: Dict[str, Dict[str, str]] = {}
    for row in review_rows:
        image_id = safe_text(row.get("Image_ID"))
        if not image_id:
            continue
        indexed[image_id] = row
    return indexed


# ============================================================
# Consolidation rules
# ============================================================

def build_review_template_rows(
    cross_rows: Sequence[Dict[str, str]],
    review_rows_by_id: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Build a reviewer-facing template from current Node C rows.

    Existing manual entries from review_pool.csv are preserved, so rerunning
    Node D does not wipe reviewer work.
    """
    template_rows: List[Dict[str, Any]] = []

    for row in cross_rows:
        if not parse_bool(row.get("Review_Needed")):
            continue

        image_id = safe_text(row.get("Image_ID"))
        manual_row = review_rows_by_id.get(image_id, {})
        merged = dict(row)
        for field in MANUAL_REVIEW_FIELDS:
            merged[field] = manual_row.get(field, "")
        template_rows.append(merged)

    return template_rows


def infer_auto_decision(cross_row: Dict[str, str]) -> Tuple[str, str]:
    """
    Decide how to handle records that have no manual row.

    Node C already marked obvious review cases. Records that do not need review
    can safely pass through as auto accepted; review-needed rows remain pending.
    """
    if parse_bool(cross_row.get("Review_Needed")):
        return "pending", "pending_manual_review"

    curation_status = safe_text(cross_row.get("Curation_Status")).lower()
    if curation_status == "reject":
        return "reject", "auto_rejected_by_node_b_or_c"

    return "accept", "auto_accepted_no_review_needed"


def apply_manual_review(
    cross_row: Dict[str, str],
    manual_row: Dict[str, str],
) -> Dict[str, Any]:
    image_id = safe_text(cross_row.get("Image_ID"))
    review_needed = parse_bool(cross_row.get("Review_Needed"))
    auto_status = safe_text(manual_row.get("_NodeD_Auto_Status"))
    normalized_decision = normalize_manual_decision(manual_row.get("Manual_Decision"))
    correction_exists = has_manual_correction(manual_row)

    if auto_status:
        node_d_status = auto_status
        node_d_decision = normalized_decision
    elif normalized_decision == "unknown":
        node_d_status = "manual_decision_unknown"
        node_d_decision = "pending"
    elif normalized_decision == "pending" and review_needed:
        node_d_status = "pending_manual_review"
        node_d_decision = "pending"
    elif normalized_decision == "pending":
        node_d_decision, node_d_status = infer_auto_decision(cross_row)
    elif normalized_decision == "revise":
        node_d_status = "manual_revised"
        node_d_decision = "accept"
    else:
        node_d_status = f"manual_{normalized_decision}"
        node_d_decision = normalized_decision

    if not auto_status and normalized_decision == "accept" and correction_exists:
        node_d_status = "manual_accepted_with_corrections"

    final_category = (
        safe_text(manual_row.get("Manual_Category"))
        or safe_text(cross_row.get("Image_Category"))
        or "unclear"
    )
    final_color = (
        safe_text(manual_row.get("Corrected_Color"))
        or safe_text(cross_row.get("Primary_Color"))
        or "unclear"
    )
    final_material = (
        safe_text(manual_row.get("Corrected_Material"))
        or safe_text(cross_row.get("Material_Clue"))
        or "unclear"
    )
    final_scenario = (
        safe_text(manual_row.get("Corrected_Scenario"))
        or safe_text(cross_row.get("Scenario"))
        or "Unclear"
    )
    final_pain_point = (
        safe_text(manual_row.get("Corrected_Pain_Point"))
        or safe_text(cross_row.get("Text_Pain_Points"))
        or "none"
    )

    visual_status = safe_text(cross_row.get("Curation_Status")) or "review"
    if node_d_decision == "reject":
        final_curation_status = "reject"
        final_confidence = 0.0
    elif node_d_decision == "pending":
        final_curation_status = "review"
        final_confidence = clamp_float(cross_row.get("Final_Confidence"), default=0.0)
    else:
        final_curation_status = "use" if visual_status != "reject" else "review"
        confidence_boost = 0.08 if normalized_decision in {"accept", "revise"} else 0.0
        final_confidence = clamp_float(
            clamp_float(cross_row.get("Final_Confidence"), default=0.0) + confidence_boost
        )

    reviewed_at = safe_text(manual_row.get("Reviewed_At"))
    if not auto_status and is_review_row_filled(manual_row) and not reviewed_at:
        reviewed_at = datetime.now().strftime("%Y-%m-%d")

    result = dict(cross_row)
    for field in MANUAL_REVIEW_FIELDS:
        result[field] = manual_row.get(field, "")

    result.update(
        {
            "Image_ID": image_id,
            "NodeD_Review_Status": node_d_status,
            "NodeD_Decision": node_d_decision,
            "NodeD_Reviewer": safe_text(manual_row.get("Reviewer")),
            "NodeD_Reviewed_At": reviewed_at,
            "NodeD_Notes": safe_text(manual_row.get("Manual_Notes")),
            "Final_Curation_Status": final_curation_status,
            "Final_Image_Category": final_category,
            "Final_Primary_Color": final_color,
            "Final_Material_Clue": final_material,
            "Final_Scenario": final_scenario,
            "Final_Pain_Point": final_pain_point,
            "Reviewed_Final_Confidence": round(final_confidence, 4),
        }
    )
    return result


def consolidate_reviews(
    cross_rows: Sequence[Dict[str, str]],
    review_rows_by_id: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    reviewed_rows: List[Dict[str, Any]] = []

    for cross_row in cross_rows:
        image_id = safe_text(cross_row.get("Image_ID"))
        manual_row = review_rows_by_id.get(image_id, {})

        if not manual_row:
            auto_decision, auto_status = infer_auto_decision(cross_row)
            manual_row = {
                "Manual_Decision": auto_decision if auto_decision != "pending" else "",
                "Manual_Notes": auto_status,
                "_NodeD_Auto_Status": auto_status,
            }

        reviewed_rows.append(apply_manual_review(cross_row, manual_row))

    return reviewed_rows


def select_final_curated_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        row for row in rows
        if safe_text(row.get("NodeD_Decision")) == "accept"
        and safe_text(row.get("Final_Curation_Status")) == "use"
    ]


def select_pending_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        row for row in rows
        if safe_text(row.get("NodeD_Decision")) == "pending"
    ]


def save_human_review_log(
    cross_rows: Sequence[Dict[str, str]],
    review_rows: Sequence[Dict[str, str]],
    reviewed_rows: Sequence[Dict[str, Any]],
    final_rows: Sequence[Dict[str, Any]],
    pending_rows: Sequence[Dict[str, Any]],
) -> None:
    decision_counter = Counter(safe_text(row.get("NodeD_Decision")) for row in reviewed_rows)
    status_counter = Counter(safe_text(row.get("NodeD_Review_Status")) for row in reviewed_rows)
    manual_filled_count = sum(1 for row in review_rows if is_review_row_filled(row))

    log_data = {
        "node": "Node D - Human Review Consolidator",
        "description": (
            "Consolidates manual review decisions from review_pool.csv with Node C "
            "cross-checked records and exports final curated records."
        ),
        "input_cross_checked_records": len(cross_rows),
        "input_review_pool_records": len(review_rows),
        "manual_filled_review_records": manual_filled_count,
        "reviewed_records": len(reviewed_rows),
        "final_curated_records": len(final_rows),
        "pending_review_records": len(pending_rows),
        "decision_breakdown": dict(decision_counter),
        "status_breakdown": dict(status_counter),
        "review_template_csv": str(HUMAN_REVIEW_TEMPLATE_CSV),
        "human_reviewed_records_csv": str(HUMAN_REVIEWED_RECORDS_CSV),
        "human_review_pending_csv": str(HUMAN_REVIEW_PENDING_CSV),
        "final_curated_records_csv": str(FINAL_CURATED_RECORDS_CSV),
    }

    with HUMAN_REVIEW_LOG_JSON.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


# ============================================================
# Main process
# ============================================================

def run_human_reviewer() -> Dict[str, Any]:
    ensure_output_dirs()

    cross_rows = read_csv_rows(CROSS_CHECKED_RECORDS_CSV)
    if not cross_rows:
        raise FileNotFoundError(
            f"Cannot find Node C records: {CROSS_CHECKED_RECORDS_CSV}. "
            "Please run node_c_semantic_cross_checker.py first."
        )

    review_rows = read_csv_rows(SEMANTIC_REVIEW_POOL_CSV)
    review_rows_by_id = index_review_rows(review_rows)

    template_rows = build_review_template_rows(cross_rows, review_rows_by_id)
    reviewed_rows = consolidate_reviews(cross_rows, review_rows_by_id)
    final_rows = select_final_curated_rows(reviewed_rows)
    pending_rows = select_pending_rows(reviewed_rows)

    base_fields = list(cross_rows[0].keys())
    review_template_fields = ordered_fieldnames(base_fields, MANUAL_REVIEW_FIELDS)
    reviewed_fields = ordered_fieldnames(base_fields, MANUAL_REVIEW_FIELDS, NODE_D_FIELDS)
    final_fields = reviewed_fields

    write_csv(HUMAN_REVIEW_TEMPLATE_CSV, review_template_fields, template_rows)
    write_csv(HUMAN_REVIEWED_RECORDS_CSV, reviewed_fields, reviewed_rows)
    write_csv(HUMAN_REVIEW_PENDING_CSV, reviewed_fields, pending_rows)
    write_csv(FINAL_CURATED_RECORDS_CSV, final_fields, final_rows)

    save_human_review_log(
        cross_rows=cross_rows,
        review_rows=review_rows,
        reviewed_rows=reviewed_rows,
        final_rows=final_rows,
        pending_rows=pending_rows,
    )

    return {
        "cross_checked_records": len(cross_rows),
        "review_pool_records": len(review_rows),
        "template_records": len(template_rows),
        "reviewed_records": len(reviewed_rows),
        "final_curated_records": len(final_rows),
        "pending_review_records": len(pending_rows),
        "review_template_csv": str(HUMAN_REVIEW_TEMPLATE_CSV),
        "human_reviewed_records_csv": str(HUMAN_REVIEWED_RECORDS_CSV),
        "human_review_pending_csv": str(HUMAN_REVIEW_PENDING_CSV),
        "final_curated_records_csv": str(FINAL_CURATED_RECORDS_CSV),
        "log_json": str(HUMAN_REVIEW_LOG_JSON),
    }


def main() -> None:
    print("Node D human review consolidation started...")
    summary = run_human_reviewer()
    print(f"Cross-checked records: {summary['cross_checked_records']}")
    print(f"Review pool records: {summary['review_pool_records']}")
    print(f"Review template records: {summary['template_records']}")
    print(f"Reviewed records: {summary['reviewed_records']}")
    print(f"Final curated records: {summary['final_curated_records']}")
    print(f"Pending review records: {summary['pending_review_records']}")
    print(f"Review template CSV: {summary['review_template_csv']}")
    print(f"Reviewed records CSV: {summary['human_reviewed_records_csv']}")
    print(f"Pending review CSV: {summary['human_review_pending_csv']}")
    print(f"Final curated CSV: {summary['final_curated_records_csv']}")
    print(f"Log JSON: {summary['log_json']}")
    print("Node D human review consolidation completed.")


if __name__ == "__main__":
    main()
