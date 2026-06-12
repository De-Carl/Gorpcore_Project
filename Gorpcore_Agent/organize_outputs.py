"""
Organize Gorpcore Agent outputs into categorized delivery folders.

The original files are kept in Gorpcore_Agent/output because the node scripts
use those canonical paths. This script copies them into output/organized_outputs
for easier project submission and review.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, List, Tuple

from config import OUTPUT_DIR


ORGANIZED_DIR = OUTPUT_DIR / "organized_outputs"


GROUPS: List[Tuple[str, Iterable[str]]] = [
    (
        "00_conclusion_deliverables",
        [
            "final_curated_records.csv",
            "human_reviewed_records.csv",
            "human_review_completed.csv",
            "human_review_decision_summary.csv",
            "human_review_log.json",
            "semantic_cross_check_log.json",
            "vision_annotation_log.json",
            "quality_filter_log.json",
            "visualizations",
        ],
    ),
    (
        "01_node_a_quality_gatekeeper",
        [
            "image_index.csv",
            "quality_filtered_images.csv",
            "quality_filter_log.json",
            "random_dataset_contact_sheet.jpg",
            "current_dataset_contact_sheet.jpg",
            "landscape_filtered_sheet.jpg",
            "landscape_candidate_review_sheet.jpg",
            "top_nature_color_sheet.jpg",
        ],
    ),
    (
        "02_node_b_vision_annotation",
        [
            "json_labels",
            "json_labels_archive",
            "vision_annotation_log.json",
            "vision_curation_log.csv",
            "annotation_errors.csv",
        ],
    ),
    (
        "03_node_c_semantic_cross_check",
        [
            "cross_checked_records.csv",
            "review_pool.csv",
            "semantic_cross_check_log.json",
        ],
    ),
    (
        "04_node_d_human_review",
        [
            "human_review_template.csv",
            "human_review_completed.csv",
            "human_review_decision_summary.csv",
            "human_reviewed_records.csv",
            "human_review_pending.csv",
            "human_review_log.json",
        ],
    ),
    (
        "05_visualizations",
        [
            "visualizations",
        ],
    ),
    (
        "06_text_analysis_auxiliary",
        [
            "text_analysis",
        ],
    ),
]


def copy_item(source: Path, destination: Path) -> None:
    if not source.exists():
        return

    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write_readme(copied_items: List[Tuple[str, str]]) -> None:
    lines = [
        "# Organized Gorpcore Agent Outputs",
        "",
        "This folder contains categorized copies of files from `Gorpcore_Agent/output`.",
        "The original output root is intentionally kept unchanged so the node scripts can still run with their canonical paths.",
        "",
        "## Folders",
        "",
        "- `00_conclusion_deliverables`: final curated dataset, review summary, key logs, and report-ready visualizations.",
        "- `01_node_a_quality_gatekeeper`: image index, quality filtering outputs, and contact sheets.",
        "- `02_node_b_vision_annotation`: Qwen-VL-Max JSON labels and vision annotation logs.",
        "- `03_node_c_semantic_cross_check`: semantic consistency table and review pool.",
        "- `04_node_d_human_review`: completed human review tables and consolidation log.",
        "- `05_visualizations`: generated chart PNGs and visualization summary.",
        "- `06_text_analysis_auxiliary`: optional text-analysis artifacts used as auxiliary input.",
        "",
        "## Copied Items",
        "",
    ]
    for group, item in copied_items:
        lines.append(f"- `{group}/{item}`")
    (ORGANIZED_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def organize_outputs() -> List[Tuple[str, str]]:
    ORGANIZED_DIR.mkdir(parents=True, exist_ok=True)
    copied_items: List[Tuple[str, str]] = []

    for group_name, items in GROUPS:
        group_dir = ORGANIZED_DIR / group_name
        group_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            source = OUTPUT_DIR / item
            destination = group_dir / source.name
            if source.exists():
                copy_item(source, destination)
                copied_items.append((group_name, source.name))

    write_readme(copied_items)
    return copied_items


def main() -> None:
    copied_items = organize_outputs()
    print(f"Organized output directory: {ORGANIZED_DIR}")
    print(f"Copied items: {len(copied_items)}")
    for group, item in copied_items:
        print(f"  - {group}/{item}")


if __name__ == "__main__":
    main()
