# Data Dictionary, Metadata & Version Control

> Documents the **metadata** and **version-control** stages of the curation
> pipeline (course brief: "documented curation pipeline: collection → cleaning →
> **metadata** → **version control**"). It defines every field in the curated
> feature database and records how dataset versions are tracked.

---

## 1. Dataset versions

The project uses an explicit, named versioning scheme. Each stage produces a
distinct, frozen artifact so results are reproducible and changes are traceable.

| Version | Stage | Artifact(s) | Rows | What it is |
| --- | --- | --- | --- | --- |
| **v0** | Collection | `Dataset/**/*.json` | ~39,602 text · 1,077 images | Raw scraped data, per platform |
| **v1** | Cleaning (Node A) | `quality_filtered_images.csv` | 1,077 → 946 | Images passing the quality gate |
| **v2** | Annotation (Node B/C) | `cross_checked_records.csv`, `json_labels/*.json` | 946 | Vision labels + image↔text cross-check |
| **v3** | Human review (Node D) | `final_curated_records.csv`, `human_review_log.json` | 946 | Auditable, human-approved curation |
| **v4** | Fusion | `feature_database.csv` | 946 | Image + text features joined (see §3) |

**Stable identifiers (the join keys across all versions):**
- `Image_ID` = `GRP-XHS-{note_id}-{image_index}` — one row per image, stable across stages.
- `Source_ID` = `GRP-XHS-{note_id}` — groups all images from one Xiaohongshu note.

These IDs are generated once in `data_loader.py` and never change, so any record
can be traced from the final database back to its raw v0 source.

---

## 2. Version control practices

- **Code & docs:** tracked in **git** (`main` branch). Each pipeline node is a
  separate, single-responsibility script so changes are isolated and reviewable.
- **Configuration:** all paths and thresholds are centralised in
  `Gorpcore_Agent/config.py` (root derived from file location → portable, no
  absolute paths), so a config change is one diff, not a scattered edit.
- **Data artifacts:** intermediate CSV/JSON outputs are versioned by **stage and
  filename** (table in §1) rather than overwritten in place, so each stage's output
  is independently auditable.
- **Run logs:** every node writes a JSON/CSV log (`quality_filter_log.json`,
  `vision_annotation_log.csv`, `semantic_cross_check_log.json`,
  `human_review_log.json`) recording counts and decisions for that run.
- **⚠️ Do not version-control secrets.** `Dataset/xhs/xiaohongshu_auth_state.json`
  (login cookie) must be removed from tracking and `.gitignore`d — see
  [ETHICS_AND_RISK.md](./ETHICS_AND_RISK.md) §2.2.

---

## 3. Data dictionary — `feature_database.csv` (v4, 946 rows)

The fused feature database is the single source of truth behind the website and
the report. Fields are grouped by origin.

### 3.1 Identifiers & provenance
| Column | Type | Description |
| --- | --- | --- |
| `Image_ID` | string | Unique per-image ID, `GRP-XHS-{note_id}-{idx}` |
| `note_id` | string | Source Xiaohongshu note ID |
| `Source_ID` | string | Note-level group ID, `GRP-XHS-{note_id}` |
| `keyword` | string | Search hashtag the post was collected under |
| `title_text` | string | Note title |
| `raw_text` | string | Full note body (used for text analysis) |
| `publish_time_resolved` | date | Normalised publish date |
| `image_path` | string | Project-relative path to the curated image |

### 3.2 Image-derived visual features
| Column | Type | Description |
| --- | --- | --- |
| `Primary_HEX` | hex | Dominant colour (MiniBatch K-Means) |
| `Secondary_HEX` | hex | Secondary colour |
| `Dominant_Color_Name` | string | Named colour for `Primary_HEX` |
| `Color_Family` | string | Bucketed colour family (olive, khaki, black…) |
| `Pockets` | int / — | Pocket count *(visual label only; else —)* |
| `Zipper_Type` | enum / — | e.g. Sealed *(visual label only)* |
| `Drawcord` | bool / — | Present? *(visual label only)* |
| `Buckle` | bool / — | Present? *(visual label only)* |
| `Reflective` | bool / — | Reflective detailing? |
| `Hood` | bool / — | Hood present? |
| `Fit` | enum / — | Loose / Regular / … *(often unknown)* |
| `Scenario` | enum / — | Outdoor / Urban / … |
| `Visual_Weight` | float / — | Demo-stage visual prominence (limited coverage) |

### 3.3 Text-derived features (joined by note)
| Column | Type | Description |
| --- | --- | --- |
| `Text_Keywords` | list | Top keywords from the note/comments |
| `Text_Pain_Points` | list | Matched pain points (price, breathability…) |
| `Text_Sentiment` | enum | positive / neutral / negative |
| `Text_Sentiment_Score` | float | Sentiment polarity |
| `Text_Color_Terms` | list | Colour words mentioned in text |
| `Text_Material_Terms` | list | Material words mentioned in text |
| `Text_Function_Terms` | list | Function words (pocket, waterproof…) |
| `Text_Scenario_Terms` | list | Scenario words (commute, hiking…) |
| `Gorpcore_Relevance` | float | How on-theme the text is |

### 3.4 Quality / confidence metadata
| Column | Type | Description |
| --- | --- | --- |
| `Final_Confidence` | float | Combined confidence after cross-check |
| `Component_Source` | enum | **`node_b` / `text_heuristic` / `unknown`** — provenance of the component fields (§3.2). Drives the website's per-record tag. |
| `Component_Confidence` | float | Confidence of component attribution |
| `Color_Extraction_Status` | enum | `ok` if K-Means succeeded |

**Coverage note:** of 946 rows, component attribution is `text_heuristic` for 198
and `unknown` for 748 (only 3 carry true `node_b` vision labels). 497 rows are
cross-linked to text. Empty visual fields are stored as `—`, never invented.

---

## 4. Per-source raw metadata

Each platform folder under `Dataset/` ships a `说明.txt` documenting that source's
file layout and JSON field meanings (e.g. `Dataset/xhs/说明.txt` defines `note_id`,
`raw_text`, `downloaded_image_paths`, etc.). Those are the authoritative
field-level docs for the **v0 raw** layer; this file documents the **curated v4**
layer they feed into.
