"""
Generate visual analytics for the Gorpcore Agent outputs.

The script intentionally uses only the standard library plus Pillow, because the
project runtime may not have matplotlib installed. It writes report-ready PNG
charts under Gorpcore_Agent/output/visualizations.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import OUTPUT_DIR


VISUALIZATION_DIR = OUTPUT_DIR / "visualizations"
SUMMARY_MD = VISUALIZATION_DIR / "visualization_summary.md"

CANVAS_W = 1280
CANVAS_H = 820
BG = "#f7f4ef"
INK = "#212121"
MUTED = "#6a6a6a"
GRID = "#ddd6cc"
ACCENT = "#2f6f73"
ACCENT_2 = "#bd6f2f"
ACCENT_3 = "#6b7f3f"
BAD = "#a94442"
WARN = "#c89b2c"
GOOD = "#3f7f55"

PALETTE = [
    "#2f6f73",
    "#bd6f2f",
    "#6b7f3f",
    "#8b5e83",
    "#b64b3c",
    "#4f6d9f",
    "#9b7a3c",
    "#5a6d61",
    "#a15c38",
    "#6f5a8d",
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_TITLE = font(34, bold=True)
FONT_SUBTITLE = font(20)
FONT_LABEL = font(18)
FONT_SMALL = font(15)
FONT_TINY = font(13)


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


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def split_terms(value: Any) -> List[str]:
    text = safe_text(value)
    if not text:
        return []
    return [
        part.strip()
        for part in text.replace(";", "|").split("|")
        if part.strip() and part.strip().lower() not in {"none", "unclear"}
    ]


def new_canvas(title: str, subtitle: str = "") -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
    draw = ImageDraw.Draw(img)
    draw.text((60, 40), title, fill=INK, font=FONT_TITLE)
    if subtitle:
        draw.text((60, 84), subtitle, fill=MUTED, font=FONT_SUBTITLE)
    draw.line((60, 125, CANVAS_W - 60, 125), fill=GRID, width=2)
    return img, draw


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> Tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_footer(draw: ImageDraw.ImageDraw, source: str) -> None:
    draw.text((60, CANVAS_H - 48), source, fill=MUTED, font=FONT_TINY)


def save_chart(img: Image.Image, name: str) -> Path:
    VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)
    path = VISUALIZATION_DIR / name
    img.save(path)
    return path


def shorten(text: str, length: int = 24) -> str:
    return text if len(text) <= length else text[: length - 1] + "..."


def bar_chart(
    title: str,
    subtitle: str,
    items: Sequence[Tuple[str, int]],
    output_name: str,
    *,
    x: int = 360,
    y: int = 165,
    width: int = 760,
    bar_h: int = 34,
    gap: int = 18,
    source: str = "",
) -> Path:
    img, draw = new_canvas(title, subtitle)
    if not items:
        draw.text((80, 180), "No data", fill=MUTED, font=FONT_LABEL)
        return save_chart(img, output_name)

    max_value = max(value for _, value in items) or 1
    for index, (label, value) in enumerate(items):
        top = y + index * (bar_h + gap)
        if top + bar_h > CANVAS_H - 90:
            break
        color = PALETTE[index % len(PALETTE)]
        label_text = shorten(label, 30)
        draw.text((80, top + 5), label_text, fill=INK, font=FONT_LABEL)
        draw.rounded_rectangle((x, top, x + width, top + bar_h), radius=8, fill="#ebe3d8")
        bar_w = int(width * value / max_value)
        draw.rounded_rectangle((x, top, x + bar_w, top + bar_h), radius=8, fill=color)
        draw.text((x + bar_w + 12, top + 5), str(value), fill=INK, font=FONT_LABEL)

    if source:
        draw_footer(draw, source)
    return save_chart(img, output_name)


def vertical_bar_chart(
    title: str,
    subtitle: str,
    items: Sequence[Tuple[str, int]],
    output_name: str,
    *,
    source: str = "",
) -> Path:
    img, draw = new_canvas(title, subtitle)
    if not items:
        return save_chart(img, output_name)

    chart_left, chart_top = 90, 170
    chart_w, chart_h = 1100, 470
    max_value = max(value for _, value in items) or 1

    for tick in range(0, 6):
        y = chart_top + chart_h - tick * chart_h / 5
        draw.line((chart_left, y, chart_left + chart_w, y), fill=GRID, width=1)
        label = str(round(max_value * tick / 5))
        draw.text((45, y - 8), label, fill=MUTED, font=FONT_TINY)

    bar_gap = 18
    bar_w = max(24, int((chart_w - bar_gap * (len(items) + 1)) / len(items)))
    for index, (label, value) in enumerate(items):
        x = chart_left + bar_gap + index * (bar_w + bar_gap)
        h = int(chart_h * value / max_value)
        y = chart_top + chart_h - h
        draw.rounded_rectangle((x, y, x + bar_w, chart_top + chart_h), radius=8, fill=PALETTE[index % len(PALETTE)])
        value_text = str(value)
        tw, _ = text_size(draw, value_text, FONT_SMALL)
        draw.text((x + (bar_w - tw) / 2, y - 24), value_text, fill=INK, font=FONT_SMALL)
        label_text = shorten(label, 13)
        tw, _ = text_size(draw, label_text, FONT_TINY)
        draw.text((x + (bar_w - tw) / 2, chart_top + chart_h + 14), label_text, fill=INK, font=FONT_TINY)

    if source:
        draw_footer(draw, source)
    return save_chart(img, output_name)


def pie_chart(
    title: str,
    subtitle: str,
    items: Sequence[Tuple[str, int]],
    output_name: str,
    *,
    source: str = "",
) -> Path:
    img, draw = new_canvas(title, subtitle)
    total = sum(value for _, value in items) or 1
    bbox = (90, 190, 570, 670)
    start = -90
    for index, (label, value) in enumerate(items):
        angle = 360 * value / total
        draw.pieslice(bbox, start, start + angle, fill=PALETTE[index % len(PALETTE)], outline=BG)
        start += angle

    legend_x = 660
    legend_y = 190
    for index, (label, value) in enumerate(items):
        y = legend_y + index * 50
        draw.rounded_rectangle((legend_x, y, legend_x + 28, y + 28), radius=6, fill=PALETTE[index % len(PALETTE)])
        pct = value / total * 100
        draw.text((legend_x + 42, y), f"{label}: {value} ({pct:.1f}%)", fill=INK, font=FONT_LABEL)

    if source:
        draw_footer(draw, source)
    return save_chart(img, output_name)


def funnel_chart(
    title: str,
    subtitle: str,
    items: Sequence[Tuple[str, int]],
    output_name: str,
    *,
    source: str = "",
) -> Path:
    img, draw = new_canvas(title, subtitle)
    max_value = max(value for _, value in items) or 1
    y = 175
    center = CANVAS_W // 2
    max_w = 930
    h = 74
    for index, (label, value) in enumerate(items):
        w = max(140, int(max_w * value / max_value))
        x0 = center - w // 2
        y0 = y + index * 92
        color = PALETTE[index % len(PALETTE)]
        draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=14, fill=color)
        text = f"{label}: {value}"
        tw, th = text_size(draw, text, FONT_LABEL)
        draw.text((center - tw / 2, y0 + (h - th) / 2 - 2), text, fill="white", font=FONT_LABEL)

    if source:
        draw_footer(draw, source)
    return save_chart(img, output_name)


def scatter_chart(
    title: str,
    subtitle: str,
    rows: Sequence[Dict[str, str]],
    output_name: str,
    *,
    source: str = "",
) -> Path:
    img, draw = new_canvas(title, subtitle)
    left, top, w, h = 110, 170, 980, 520
    draw.rectangle((left, top, left + w, top + h), outline=GRID, width=2)

    for tick in range(0, 6):
        x = left + tick * w / 5
        y = top + h - tick * h / 5
        draw.line((x, top, x, top + h), fill=GRID, width=1)
        draw.line((left, y, left + w, y), fill=GRID, width=1)
        label = f"{tick / 5:.1f}"
        draw.text((x - 10, top + h + 12), label, fill=MUTED, font=FONT_TINY)
        draw.text((left - 44, y - 8), label, fill=MUTED, font=FONT_TINY)

    color_by_status = {"use": GOOD, "review": WARN, "reject": BAD}
    for row in rows:
        relevance = clamp_float(row.get("Gorpcore_Relevance"))
        confidence = clamp_float(row.get("Visual_Confidence"))
        x = left + relevance * w
        y = top + h - confidence * h
        color = color_by_status.get(safe_text(row.get("Curation_Status")), ACCENT)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)

    draw.text((left + w / 2 - 80, top + h + 48), "Gorpcore relevance", fill=INK, font=FONT_LABEL)
    draw.text((28, top + h / 2 - 20), "Visual confidence", fill=INK, font=FONT_LABEL)

    legend_x = 980
    legend_y = 180
    for idx, (status, color) in enumerate(color_by_status.items()):
        y = legend_y + idx * 38
        draw.ellipse((legend_x, y, legend_x + 18, y + 18), fill=color)
        draw.text((legend_x + 28, y - 3), status, fill=INK, font=FONT_SMALL)

    if source:
        draw_footer(draw, source)
    return save_chart(img, output_name)


def term_counter(rows: Sequence[Dict[str, str]], field: str) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        counter.update(split_terms(row.get(field)))
    return counter


def generate_visualizations() -> List[Path]:
    VISUALIZATION_DIR.mkdir(parents=True, exist_ok=True)

    quality_rows = read_csv(OUTPUT_DIR / "quality_filtered_images.csv")
    cross_rows = read_csv(OUTPUT_DIR / "cross_checked_records.csv")
    final_rows = read_csv(OUTPUT_DIR / "final_curated_records.csv")
    reviewed_rows = read_csv(OUTPUT_DIR / "human_reviewed_records.csv")
    review_rows = read_csv(OUTPUT_DIR / "human_review_completed.csv")
    quality_log = read_json(OUTPUT_DIR / "quality_filter_log.json")
    vision_log = read_json(OUTPUT_DIR / "vision_annotation_log.json")
    node_d_log = read_json(OUTPUT_DIR / "human_review_log.json")

    generated: List[Path] = []

    generated.append(
        funnel_chart(
            "Agent Processing Funnel",
            "From raw candidate images to final curated outfit records",
            [
                ("Node A indexed images", int(quality_log.get("total_images", len(quality_rows)))),
                ("Node A passed", int(quality_log.get("passed", 0))),
                ("Node B visual labels", int(vision_log.get("total_candidates", 0))),
                ("Node C checked", len(cross_rows)),
                ("Final curated", len(final_rows)),
            ],
            "01_agent_processing_funnel.png",
            source="Source: quality_filter_log.json, vision_annotation_log.json, cross_checked_records.csv, final_curated_records.csv",
        )
    )

    generated.append(
        pie_chart(
            "Node B Curation Status",
            "How the vision model categorized images after quality filtering",
            list(Counter(row.get("Curation_Status", "unknown") for row in cross_rows).most_common()),
            "02_node_b_curation_status.png",
            source="Source: cross_checked_records.csv",
        )
    )

    generated.append(
        vertical_bar_chart(
            "Final Image Category Distribution",
            "Curated visual record types after Node D consolidation",
            Counter(row.get("Final_Image_Category", "unknown") for row in final_rows).most_common(10),
            "03_final_image_categories.png",
            source="Source: final_curated_records.csv",
        )
    )

    generated.append(
        vertical_bar_chart(
            "Final Scenario Distribution",
            "Use-case scenarios represented in the curated image set",
            Counter(row.get("Final_Scenario", "unknown") for row in final_rows).most_common(8),
            "04_final_scenarios.png",
            source="Source: final_curated_records.csv",
        )
    )

    generated.append(
        bar_chart(
            "Dominant Clothing Colors",
            "Top primary colors in the final curated image records",
            Counter(row.get("Final_Primary_Color", "unknown") for row in final_rows).most_common(12),
            "05_final_primary_colors.png",
            source="Source: final_curated_records.csv",
        )
    )

    generated.append(
        bar_chart(
            "Visible Material and Style Cues",
            "Most frequent material clues extracted from final image labels",
            term_counter(final_rows, "Final_Material_Clue").most_common(12),
            "06_final_material_clues.png",
            source="Source: final_curated_records.csv",
        )
    )

    generated.append(
        pie_chart(
            "Human Review Decisions",
            "Manual review outcomes for records flagged by Node C",
            Counter(row.get("Manual_Decision", "unknown") for row in review_rows).most_common(),
            "07_human_review_decisions.png",
            source="Source: human_review_completed.csv",
        )
    )

    conflict_counter: Counter = Counter()
    for row in cross_rows:
        conflict_counter.update(split_terms(row.get("Conflict_Type")))
    generated.append(
        bar_chart(
            "Semantic Conflict Types",
            "Main reasons records were down-weighted or sent to review",
            conflict_counter.most_common(10),
            "08_semantic_conflict_types.png",
            source="Source: cross_checked_records.csv",
        )
    )

    generated.append(
        scatter_chart(
            "Relevance vs Confidence",
            "Node B visual confidence by Gorpcore relevance score",
            cross_rows,
            "09_relevance_confidence_scatter.png",
            source="Source: cross_checked_records.csv",
        )
    )

    summary_lines = [
        "# Gorpcore Agent Visualization Summary",
        "",
        f"- Total Node B labels: {vision_log.get('total_candidates', len(cross_rows))}",
        f"- Final curated records: {len(final_rows)}",
        f"- Human review pending records: {node_d_log.get('pending_review_records', 0)}",
        f"- Generated charts: {len(generated)}",
        "",
        "## Chart Files",
        "",
    ]
    for path in generated:
        summary_lines.append(f"- `{path.name}`")
    SUMMARY_MD.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    return generated


def main() -> None:
    generated = generate_visualizations()
    print(f"Generated {len(generated)} visualization charts:")
    for path in generated:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
