"""
Bonus deliverable #2 — Image word cloud (photo mosaic).

Instead of a text word cloud, this builds a *visual* word cloud: the real
curated Gorpcore outfit images (the 946-image feature database) are tiled into
a mountain-range silhouette — the season's visual vocabulary, made of the corpus
itself. Images are ordered by colour family so the mosaic also reads as a rough
palette gradient.

Input : Evidence_fusion_visual_dispalys/output/feature_database.csv
Output: Evidence_fusion_visual_dispalys/output/fig_image_wordcloud.png
        website/public/charts/fig_image_wordcloud.png
"""

from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURE_DB = PROJECT_ROOT / "Evidence_fusion_visual_dispalys" / "output" / "feature_database.csv"
OUT_FIG = PROJECT_ROOT / "Evidence_fusion_visual_dispalys" / "output" / "fig_image_wordcloud.png"
WEB_FIG = PROJECT_ROOT / "website" / "public" / "charts" / "fig_image_wordcloud.png"

# Canvas / tiling parameters.
WIDTH, HEIGHT = 1920, 1200
CELL = 48                      # thumbnail size in px
BG = (28, 30, 26)              # charcoal, matches the website theme
COLS = WIDTH // CELL
ROWS = HEIGHT // CELL

# Rough colour-family ordering so the mosaic reads as a palette sweep.
FAMILY_ORDER = {
    "white": 0, "off-white": 1, "beige": 2, "khaki": 3, "yellow": 4,
    "brown": 5, "orange": 6, "red": 7, "green": 8, "olive": 8, "olive green": 8,
    "blue": 10, "navy": 11, "purple": 12, "gray": 13, "grey": 13,
    "charcoal": 14, "black": 15,
}


def mountain_mask() -> np.ndarray:
    """A filled mountain-range silhouette: True where a tile should be drawn."""
    xs = np.linspace(0, 1, COLS)
    # Sum of a few gaussian-ish peaks to make a ridge line (0=top .. 1=bottom).
    peaks = [(0.18, 0.30, 0.10), (0.40, 0.12, 0.14),
             (0.62, 0.34, 0.11), (0.84, 0.22, 0.13)]
    ridge = np.ones_like(xs)
    for cx, top, width in peaks:
        ridge = np.minimum(ridge, top + (1 - math.e ** 0) * 0
                           + (1 - np.exp(-((xs - cx) ** 2) / (2 * width ** 2))) * (1 - top))
    ridge = 0.12 + ridge * 0.78          # keep peaks below the very top edge
    ridge_rows = (ridge * ROWS).astype(int)

    mask = np.zeros((ROWS, COLS), dtype=bool)
    for c in range(COLS):
        mask[ridge_rows[c]:, c] = True   # fill from ridge line down to the base
    return mask


def load_rows() -> list[dict]:
    with open(FEATURE_DB, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: FAMILY_ORDER.get((r.get("Color_Family") or "").strip().lower(), 9))
    return rows


def thumb(path: Path) -> Image.Image | None:
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    s = min(w, h)                                   # center-crop to square
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return im.resize((CELL, CELL), Image.LANCZOS)


def main() -> None:
    mask = mountain_mask()
    rows = load_rows()
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG)

    cells = [(r, c) for r in range(ROWS) for c in range(COLS) if mask[r, c]]
    print(f"Mountain mask has {len(cells)} tiles; {len(rows)} curated images available.")

    i = 0
    placed = 0
    for (r, c) in cells:
        # Walk the image list (cycling) until we find one that loads.
        for _ in range(len(rows)):
            row = rows[i % len(rows)]
            i += 1
            t = thumb(PROJECT_ROOT / row["image_path"])
            if t is not None:
                canvas.paste(t, (c * CELL, r * CELL))
                placed += 1
                break

    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    WEB_FIG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_FIG, optimize=True)
    shutil.copyfile(OUT_FIG, WEB_FIG)
    print(f"Placed {placed} thumbnails.")
    print(f"Saved -> {OUT_FIG}")
    print(f"Saved -> {WEB_FIG}")


if __name__ == "__main__":
    main()
